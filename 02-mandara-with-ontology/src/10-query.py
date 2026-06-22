"""
Ontology-grounded RAG query over Japanese failure case reports (mandara02).

Embeds the user question, retrieves the most similar Section nodes via
Neo4j vector search, augments each with graph-traversal context (entities,
relations, and matching Mandala ontology categories), then asks Claude for
a grounded answer.

Requirements:
    OPENAI_API_KEY and ANTHROPIC_API_KEY env vars (or .env file)
    Neo4j running on bolt://localhost:7687 with mandara02 populated

Usage:
    uv run python src/05-query.py "What caused the radiation leak on the Mutsu?"
    uv run python src/05-query.py --top-k 8 "放射能漏れの原因は何ですか？"
"""
import glob
import logging
import os

import anthropic
import click
import openai
from dotenv import load_dotenv
from neo4j import GraphDatabase

from common import SECTIONS_INV

LOG = logging.getLogger(__name__)

SCRIPT_DIR   = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR      = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR      = os.path.join(PRJ_DIR, "build")
SECTIONS_DIR = os.path.join(BLD_DIR, "extract", "hf-sections")

URI      = "bolt://localhost:7687"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"

OPENAI_MODEL  = "text-embedding-3-small"
CLAUDE_MODEL  = "claude-sonnet-4-6"
DEFAULT_TOP_K = 10

SYSTEM_PROMPT = """\
You are an expert analyst of Japanese industrial failure case reports (ハイトラブル事例).
You are given retrieved sections from multiple reports, each augmented with a knowledge
graph of entities and relations extracted from that section, as well as matching categories
from the Mandala failure taxonomy (cause types, action types, result types).

Answer the user's question using ONLY the provided context.
If the answer cannot be found in the context, say so clearly.
Cite the report ID and section name when referencing a source.
"""


def embed_question(oa: openai.OpenAI, question: str) -> list[float]:
    """Embed a question using the same model as the section embeddings.

    @param oa: OpenAI client.
    @param question: natural-language question.
    @return: embedding vector as a list of floats.
    """
    return oa.embeddings.create(input=question, model=OPENAI_MODEL).data[0].embedding


def retrieve_sections(session, vector: list[float], top_k: int) -> list[dict]:
    """Vector-search Neo4j for the top-k most similar Section nodes.

    @param session: active Neo4j driver session.
    @param vector: query embedding vector.
    @param top_k: number of sections to retrieve.
    @return: list of dicts with keys report_id, slug, label, score.
    """
    return session.run(
        "CALL db.index.vector.queryNodes('section_embedding', $top_k, $vector)"
        " YIELD node AS s, score"
        " RETURN s.report_id AS report_id, s.slug AS slug, s.label AS label, score",
        top_k=top_k,
        vector=vector,
    ).data()


def fetch_section_text(report_id: str, slug: str) -> str:
    """Read the plain-text content of a section from disk.

    @param report_id: failure case identifier (e.g. ``'HA0000615'``).
    @param slug: section ASCII slug (e.g. ``'keika'``).
    @return: section text, or empty string if the file is not found.
    """
    pattern = os.path.join(SECTIONS_DIR, report_id, f"*_{slug}.txt")
    matches = sorted(glob.glob(pattern))
    if not matches:
        return ""
    with open(matches[0], encoding="utf-8") as fh:
        return fh.read().strip()


def fetch_graph_context(session, report_id: str, slug: str) -> dict:
    """Retrieve entities, relations, and ontology categories for a section.

    Traverses the graph to find:
    - Entity nodes mentioned in the section
    - Typed relations between those entities
    - Matching Mandala ontology categories (CauseType / ActionType / ResultType)
      whose names appear in the section's entity names

    @param session: active Neo4j driver session.
    @param report_id: failure case identifier.
    @param slug: section ASCII slug.
    @return: dict with ``'entities'``, ``'triples'``, and ``'ontology'`` lists.
    """
    entities = session.run(
        "MATCH (s:Section {report_id: $report_id, slug: $slug})-[:MENTIONS]->(e:Entity)"
        " RETURN e.name AS name, e.type AS type",
        report_id=report_id,
        slug=slug,
    ).data()

    triples = session.run(
        "MATCH (s:Section {report_id: $report_id, slug: $slug})-[:MENTIONS]->(a:Entity)"
        " MATCH (a)-[r]->(b:Entity)"
        " RETURN a.name AS source, type(r) AS rel, b.name AS target",
        report_id=report_id,
        slug=slug,
    ).data()

    # Look up ontology categories whose names match any entity in this section
    ontology = session.run(
        "MATCH (s:Section {report_id: $report_id, slug: $slug})-[:MENTIONS]->(e:Entity)"
        " MATCH (cat) WHERE (cat:CauseType OR cat:ActionType OR cat:ResultType)"
        "   AND cat.name = e.name"
        " RETURN labels(cat)[0] AS category_type, cat.name AS name,"
        "        cat.level AS level, cat.dimension AS dimension",
        report_id=report_id,
        slug=slug,
    ).data()

    return {"entities": entities, "triples": triples, "ontology": ontology}


def build_context_block(section: dict, text: str, graph: dict) -> str:
    """Format a section's text, graph context, and ontology matches into a prompt block.

    @param section: dict with report_id, slug, label, score.
    @param text: plain-text content of the section.
    @param graph: dict returned by fetch_graph_context.
    @return: formatted multi-line string.
    """
    label = section.get("label") or SECTIONS_INV.get(section["slug"], section["slug"])
    lines = [
        f"## {section['report_id']} / {label}（{section['slug']}）  [similarity: {section['score']:.3f}]",
        "",
        text or "(no text available)",
    ]

    if graph["entities"]:
        lines += ["", "### Entities"]
        for e in graph["entities"]:
            lines.append(f"  - {e['name']} ({e['type']})")

    if graph["triples"]:
        lines += ["", "### Relations"]
        for t in graph["triples"]:
            lines.append(f"  {t['source']} --[{t['rel']}]--> {t['target']}")

    if graph["ontology"]:
        lines += ["", "### Mandala Ontology Matches"]
        for o in graph["ontology"]:
            lines.append(f"  - [{o['category_type']} L{o['level']}] {o['name']} (dimension: {o['dimension']})")

    return "\n".join(lines)


def save_context(question: str, context_blocks: list[str], path: str) -> None:
    """Write the full LLM prompt to a file for inspection.

    @param question: user's natural-language question.
    @param context_blocks: list of formatted section+graph context strings.
    @param path: destination file path.
    """
    context = "\n\n---\n\n".join(context_blocks)
    user_content = (
        f"Context from failure case reports:\n\n{context}"
        f"\n\n---\n\nQuestion: {question}"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("=== SYSTEM ===\n\n")
        fh.write(SYSTEM_PROMPT)
        fh.write("\n\n=== USER ===\n\n")
        fh.write(user_content)
    LOG.info(f"Context saved to: {path}")


def ask_claude(client: anthropic.Anthropic, question: str, context_blocks: list[str]) -> str:
    """Send the augmented context and question to Claude and return its answer.

    @param client: Anthropic client.
    @param question: user's natural-language question.
    @param context_blocks: list of formatted section+graph+ontology context strings.
    @return: Claude's answer as plain text.
    """
    context = "\n\n---\n\n".join(context_blocks)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": (
                f"Context from failure case reports:\n\n{context}"
                f"\n\n---\n\nQuestion: {question}"
            ),
        }],
    )
    return response.content[0].text


@click.command()
@click.argument("question")
@click.option("--top-k", default=DEFAULT_TOP_K, show_default=True,
              help="Number of sections to retrieve.")
def main(question: str, top_k: int) -> None:
    """Query the ontology-grounded RAG system (mandara02) with a natural-language QUESTION."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv()

    oa     = openai.OpenAI()
    claude = anthropic.Anthropic()
    driver = GraphDatabase.driver(URI, auth=AUTH)

    try:
        LOG.info("Embedding question...")
        vector = embed_question(oa, question)

        with driver.session(database=DATABASE) as session:
            LOG.info(f"Retrieving top-{top_k} sections...")
            sections = retrieve_sections(session, vector, top_k)

            context_blocks = []
            for sec in sections:
                text  = fetch_section_text(sec["report_id"], sec["slug"])
                graph = fetch_graph_context(session, sec["report_id"], sec["slug"])
                block = build_context_block(sec, text, graph)
                context_blocks.append(block)
                LOG.info(
                    f"  {sec['report_id']}/{sec['slug']}"
                    f"  score={sec['score']:.3f}"
                    f"  entities={len(graph['entities'])}"
                    f"  triples={len(graph['triples'])}"
                    f"  ontology_matches={len(graph['ontology'])}"
                )

        context_path = os.path.join(BLD_DIR, "last_context_02.txt")
        save_context(question, context_blocks, context_path)

        LOG.info("Asking Claude...")
        answer = ask_claude(claude, question, context_blocks)

        print(f"\nQ: {question}\n")
        print(f"A: {answer}\n")

    finally:
        driver.close()


if __name__ == "__main__":
    main()

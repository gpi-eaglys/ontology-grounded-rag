"""
Ontology-grounded RAG query over Japanese failure case reports.

Compared with experiment 01's 07-query.py, this script adds a Mandala taxonomy
classification step before retrieval: Claude is forced to call a
``classify_question`` tool that maps the question to specific Mandala taxonomy
terms.  Those terms drive an additional ontology-path search in Neo4j alongside
the standard vector retrieval.  Each retrieved section is also augmented with
any taxonomy nodes its entities resolve to.

Requirements:
    OPENAI_API_KEY and ANTHROPIC_API_KEY env vars (or .env file)
    Neo4j running on bolt://localhost:7602 with mandara02 populated.
    Run 01-04 pipeline scripts first.

Usage:
    uv run python src/05-query.py "What caused the radiation leak on the Mutsu?"
    uv run python src/05-query.py --top-k 8 "放射能漏れの原因は何ですか？"
"""
import glob
import json
import logging
import os

import anthropic
import click
import openai
from dotenv import load_dotenv
from neo4j import GraphDatabase

from common import SECTIONS_INV

LOG = logging.getLogger(__name__)

SCRIPT_DIR    = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR       = os.path.join(PRJ_DIR, "build")
SECTIONS_DIR  = os.path.join(BLD_DIR, "extract", "hf-sections")
TAXONOMY_PATH = os.path.join(BLD_DIR, "mandala", "mandala_taxonomy.json")

URI      = "bolt://localhost:7602"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"

OPENAI_MODEL       = "text-embedding-3-small"
CLAUDE_MODEL       = "claude-sonnet-4-6"
DEFAULT_TOP_K      = 10
CLASSIFY_TOOL_NAME = "classify_question"

SYSTEM_PROMPT = """\
You are an expert analyst of Japanese industrial failure case reports (ハイトラブル事例).
You are given retrieved sections from multiple reports, each augmented with a knowledge
graph of entities and relations extracted from that section, and ontology matches to
the Failure Mandala taxonomy (原因/行動/結果 dimensions).

Answer the user's question using ONLY the provided context.
If the answer cannot be found in the context, say so clearly.
Cite the report ID and section name when referencing a source.
"""


def load_taxonomy() -> dict:
    """Load the Mandala taxonomy from the build cache.

    @return: parsed taxonomy dict with keys ``cause``, ``action``, ``result``.
    """
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_classify_tool(taxonomy: dict) -> dict:
    """Build the forced-tool-use JSON schema for question classification.

    Enumerates every term from all three Mandala dimensions so the model must
    select from the canonical taxonomy vocabulary.

    @param taxonomy: taxonomy dict loaded by ``load_taxonomy``.
    @return: Anthropic tool definition dict.
    """
    def all_terms(dim: dict) -> list[str]:
        terms: list[str] = []
        for item in dim["items"]:
            terms.append(item["name"])
            terms.extend(item["children"])
        return terms

    cause_terms  = all_terms(taxonomy["cause"])
    action_terms = all_terms(taxonomy["action"])
    result_terms = all_terms(taxonomy["result"])

    return {
        "name": CLASSIFY_TOOL_NAME,
        "description": (
            "Classify the user question against the Failure Mandala (失敗まんだら) taxonomy. "
            "Identify which of the three dimensions (cause/action/result) the question "
            "primarily concerns, and select the most relevant taxonomy terms from each "
            "applicable dimension."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["cause", "action", "result"]},
                    "description": "Which Mandala dimensions the question is primarily about.",
                    "minItems": 1,
                },
                "cause_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": cause_terms},
                    "description": "Relevant 原因 (cause) taxonomy terms. Empty list if cause is not a focus.",
                },
                "action_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": action_terms},
                    "description": "Relevant 行動 (action) taxonomy terms. Empty list if action is not a focus.",
                },
                "result_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": result_terms},
                    "description": "Relevant 結果 (result) taxonomy terms. Empty list if result is not a focus.",
                },
            },
            "required": ["dimensions", "cause_terms", "action_terms", "result_terms"],
        },
    }


def classify_question(client: anthropic.Anthropic, question: str, tool: dict) -> dict:
    """Force Claude to classify the question against the Mandala taxonomy.

    Uses ``tool_choice={"type": "tool", "name": CLASSIFY_TOOL_NAME}`` to
    guarantee a structured response.

    @param client: Anthropic client.
    @param question: natural-language question to classify.
    @param tool: tool definition dict returned by ``build_classify_tool``.
    @return: parsed tool input dict with keys ``dimensions``, ``cause_terms``,
        ``action_terms``, ``result_terms``.
    """
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        tools=[tool],
        tool_choice={"type": "tool", "name": CLASSIFY_TOOL_NAME},
        messages=[{
            "role": "user",
            "content": (
                "Classify the following question against the Failure Mandala taxonomy:\n\n"
                f"{question}"
            ),
        }],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == CLASSIFY_TOOL_NAME:
            return block.input
    raise RuntimeError("classify_question tool not called — unexpected API response")


def embed_question(oa: openai.OpenAI, question: str) -> list[float]:
    """Embed a question using the same model as the section embeddings.

    @param oa: OpenAI client.
    @param question: natural-language question.
    @return: embedding vector as a list of floats.
    """
    return oa.embeddings.create(input=question, model=OPENAI_MODEL).data[0].embedding


def retrieve_by_vector(session, vector: list[float], top_k: int) -> list[dict]:
    """Vector-search Neo4j for the top-k most similar Section nodes.

    @param session: active Neo4j driver session on mandara02.
    @param vector: query embedding vector.
    @param top_k: number of sections to retrieve.
    @return: list of dicts with keys ``report_id``, ``slug``, ``label``, ``score``.
    """
    return session.run(
        "CALL db.index.vector.queryNodes('section_embedding', $top_k, $vector)"
        " YIELD node AS s, score"
        " RETURN s.report_id AS report_id, s.slug AS slug, s.label AS label, score",
        top_k=top_k,
        vector=vector,
    ).data()


def retrieve_by_ontology(session, classification: dict) -> list[dict]:
    """Find Section nodes that MENTION entities matching the classified taxonomy terms.

    Looks up Entity nodes whose names appear in the classified cause/action/result
    term lists, then returns the sections that mention those entities.

    @param session: active Neo4j driver session on mandara02.
    @param classification: dict from ``classify_question``.
    @return: list of dicts with keys ``report_id``, ``slug``, ``label``, ``matched_term``.
    """
    all_terms = (
        classification.get("cause_terms", [])
        + classification.get("action_terms", [])
        + classification.get("result_terms", [])
    )
    if not all_terms:
        return []

    return session.run(
        "MATCH (s:Section)-[:MENTIONS]->(e:Entity)"
        " WHERE e.name IN $terms"
        " RETURN DISTINCT s.report_id AS report_id, s.slug AS slug,"
        "   s.label AS label, e.name AS matched_term",
        terms=all_terms,
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
    """Retrieve entities, relations, and ontology matches for a section.

    For each entity the section mentions, also traverses into the Mandala
    ontology layer to find any matching CauseType / ActionType / ResultType
    nodes by name.

    @param session: active Neo4j driver session on mandara02.
    @param report_id: failure case identifier.
    @param slug: section ASCII slug.
    @return: dict with ``'entities'``, ``'triples'``, and ``'ontology_matches'`` lists.
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

    entity_names = [e["name"] for e in entities]
    ontology_matches: list[dict] = []
    if entity_names:
        ontology_matches = session.run(
            "MATCH (n)"
            " WHERE (n:CauseType OR n:ActionType OR n:ResultType) AND n.name IN $names"
            " RETURN n.name AS name, labels(n)[0] AS ontology_label,"
            "   n.dimension AS dimension, n.group AS group, n.level AS level",
            names=entity_names,
        ).data()

    return {"entities": entities, "triples": triples, "ontology_matches": ontology_matches}


def merge_sections(vector_results: list[dict], onto_results: list[dict]) -> list[dict]:
    """Merge vector-retrieved and ontology-retrieved sections, deduplicating by (report_id, slug).

    When both pipelines return the same section, the entry is kept once with
    both ``score`` and ``matched_term`` populated.

    @param vector_results: rows from ``retrieve_by_vector`` (each has ``score``).
    @param onto_results: rows from ``retrieve_by_ontology`` (each has ``matched_term``).
    @return: deduplicated merged list.
    """
    merged: dict[tuple[str, str], dict] = {}
    for row in vector_results:
        key = (row["report_id"], row["slug"])
        merged[key] = dict(row)

    for row in onto_results:
        key = (row["report_id"], row["slug"])
        if key in merged:
            merged[key]["matched_term"] = row["matched_term"]
        else:
            merged[key] = {
                "report_id":    row["report_id"],
                "slug":         row["slug"],
                "label":        row["label"],
                "score":        None,
                "matched_term": row["matched_term"],
            }

    return list(merged.values())


def build_context_block(
    section: dict,
    text: str,
    graph: dict,
    matched_term: str | None = None,
) -> str:
    """Format a section's text, graph, and ontology context into a prompt block.

    @param section: dict with report_id, slug, label, and optionally score.
    @param text: plain-text content of the section.
    @param graph: dict returned by ``fetch_graph_context``.
    @param matched_term: ontology term that triggered retrieval of this section, or None.
    @return: formatted multi-line string.
    """
    label     = section.get("label") or SECTIONS_INV.get(section["slug"], section["slug"])
    score_str = f"  [similarity: {section['score']:.3f}]" if section.get("score") else ""
    onto_str  = f"  [ontology match: {matched_term}]" if matched_term else ""
    lines = [
        f"## {section['report_id']} / {label}（{section['slug']}）{score_str}{onto_str}",
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

    if graph["ontology_matches"]:
        lines += ["", "### Mandala Ontology Matches"]
        for m in graph["ontology_matches"]:
            lines.append(
                f"  - {m['name']}  ({m['ontology_label']}, level {m['level']},"
                f" group: {m['group']})"
            )

    return "\n".join(lines)


def save_context(
    question: str,
    classification: dict,
    context_blocks: list[str],
    path: str,
) -> None:
    """Write the full LLM prompt and classification to a file for inspection.

    @param question: user's natural-language question.
    @param classification: dict from ``classify_question``.
    @param context_blocks: list of formatted section+graph+ontology context strings.
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
        fh.write("\n\n=== CLASSIFICATION ===\n\n")
        fh.write(json.dumps(classification, ensure_ascii=False, indent=2))
        fh.write("\n\n=== USER ===\n\n")
        fh.write(user_content)
    LOG.info("Context saved to: %s", path)


def ask_claude(
    client: anthropic.Anthropic,
    question: str,
    context_blocks: list[str],
) -> str:
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
              help="Number of sections to retrieve via vector search.")
def main(question: str, top_k: int) -> None:
    """
    Query the ontology-grounded RAG system with a natural-language QUESTION.

    The question is first classified against the Failure Mandala taxonomy via
    forced tool use; matching taxonomy terms drive an additional ontology-path
    search in Neo4j alongside the standard vector retrieval.
    """
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
        taxonomy = load_taxonomy()
        tool     = build_classify_tool(taxonomy)

        LOG.info("Classifying question against Mandala taxonomy...")
        classification = classify_question(claude, question, tool)
        LOG.info(
            "Classification: dimensions=%s  cause=%s  action=%s  result=%s",
            classification["dimensions"],
            classification["cause_terms"],
            classification["action_terms"],
            classification["result_terms"],
        )

        LOG.info("Embedding question...")
        vector = embed_question(oa, question)

        with driver.session(database=DATABASE) as session:
            LOG.info("Retrieving top-%d sections by vector...", top_k)
            vector_results = retrieve_by_vector(session, vector, top_k)

            LOG.info("Retrieving sections by ontology term match...")
            onto_results = retrieve_by_ontology(session, classification)

            sections = merge_sections(vector_results, onto_results)
            LOG.info(
                "Total sections: %d vector + %d ontology = %d merged",
                len(vector_results), len(onto_results), len(sections),
            )

            context_blocks: list[str] = []
            for sec in sections:
                text  = fetch_section_text(sec["report_id"], sec["slug"])
                graph = fetch_graph_context(session, sec["report_id"], sec["slug"])
                block = build_context_block(sec, text, graph, sec.get("matched_term"))
                context_blocks.append(block)
                LOG.info(
                    "  %s/%s  score=%s  entities=%d  triples=%d  onto=%d%s",
                    sec["report_id"],
                    sec["slug"],
                    f"{sec['score']:.3f}" if sec.get("score") else "n/a",
                    len(graph["entities"]),
                    len(graph["triples"]),
                    len(graph["ontology_matches"]),
                    f"  matched={sec['matched_term']}" if sec.get("matched_term") else "",
                )

        context_path = os.path.join(BLD_DIR, "last_context_02.txt")
        save_context(question, classification, context_blocks, context_path)

        LOG.info("Asking Claude...")
        answer = ask_claude(claude, question, context_blocks)

        print(f"\nQ: {question}\n")
        print(f"A: {answer}\n")

    finally:
        driver.close()


if __name__ == "__main__":
    main()

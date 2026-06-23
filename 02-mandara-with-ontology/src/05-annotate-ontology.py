"""
Classify each Section into the Mandala ontology by writing CLASSIFIED_AS edges.

For every Section node in mandara02 that has text on disk, Claude is asked
(via forced tool use) which CauseType / ActionType / ResultType taxonomy terms
apply.  The answer is written back as:

    (Section)-[:CLASSIFIED_AS {dimension}]->(CauseType | ActionType | ResultType)

Edges are MERGE-d so the script is safe to re-run.  Sections that already have
at least one CLASSIFIED_AS edge are skipped unless --force is passed.
Non-substantive sections (bibliography, title) are always skipped.

Requirements:
    ANTHROPIC_API_KEY env var (or .env file)
    Neo4j running on bolt://localhost:7602 with mandara02 populated.
    Run 01-04 pipeline scripts first.

Usage:
    uv run python src/05-annotate-ontology.py
    uv run python src/05-annotate-ontology.py --force
"""
import glob
import json
import logging
import os
import re

import anthropic
import click
from dotenv import load_dotenv
from neo4j import GraphDatabase

from common import SECTIONS_INV

LOG = logging.getLogger(__name__)

SCRIPT_DIR    = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR       = os.path.join(PRJ_DIR, "build")
SECTIONS_DIR  = os.path.join(BLD_DIR, "extract", "hf-sections")
ONTOLOGY_DIR  = os.path.join(BLD_DIR, "extract", "hf-ontology")
TAXONOMY_PATH = os.path.join(BLD_DIR, "mandala", "mandala_taxonomy.json")

URI      = "bolt://localhost:7602"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"

CLAUDE_MODEL       = "claude-sonnet-4-6"
CLASSIFY_TOOL_NAME = "classify_section"

# Maps dimension key → Neo4j node label
DIM_LABEL: dict[str, str] = {
    "cause":  "CauseType",
    "action": "ActionType",
    "result": "ResultType",
}

# Sections that carry no failure-analysis content — never classified.
SKIP_SLUGS: frozenset[str] = frozenset({"pre", "bib"})

# Per-section hints about which Mandala dimensions are primary.
# Passed as a system message so the model knows where to focus.
SECTION_HINTS: dict[str, str] = {
    "jisho":      "This is the 事象 (incident/phenomenon) section. Focus on 結果 (result) terms; "
                  "note any 原因 or 行動 terms only if clearly stated.",
    "keika":      "This is the 経過 (sequence of events) section. Focus on 結果 (result) and "
                  "行動 (action) terms; include 原因 terms only if explicitly discussed.",
    "genin":      "This is the 原因 (cause analysis) section. Focus on 原因 (cause) terms. "
                  "Include 行動 or 結果 terms only if they appear as contributing factors.",
    "taisho":     "This is the 対処 (immediate response) section. Focus on 行動 (action) terms.",
    "taisaku":    "This is the 対策 (preventive measures) section. Focus on 行動 (action) terms.",
    "sokatsu":    "This is the 総括 (summary) section. All three dimensions may be present.",
    "chishikika": "This is the 知識化 (lessons learned) section. All three dimensions may be present.",
    "haikei":     "This is the 背景 (background) section. Focus on 原因 (cause) terms that set "
                  "the context; 行動 and 結果 terms are secondary.",
    "yomoyama":   "This is the 四方山話 (side notes) section. Classify only terms clearly evidenced "
                  "in the text; all three dimensions are possible.",
    "gojitsudan": "This is the 後日談 (postscript) section. Classify only terms clearly evidenced "
                  "in the text; all three dimensions are possible.",
}


def load_taxonomy() -> dict:
    """
    Loads the Mandala taxonomy from the build cache.

    @return: parsed taxonomy dict with keys ``cause``, ``action``, ``result``.
    """
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_classify_tool(taxonomy: dict) -> dict:
    """
    Builds the forced-tool-use JSON schema for section classification.

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
            "Classify the section text against the Failure Mandala (失敗まんだら) taxonomy. "
            "Select the most relevant taxonomy terms from each of the three dimensions "
            "(cause / action / result) that are evidenced in the text. "
            "Use empty arrays for dimensions not covered by this section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": cause_terms},
                    "description": "Applicable 原因 (cause) taxonomy terms.",
                },
                "action_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": action_terms},
                    "description": "Applicable 行動 (action) taxonomy terms.",
                },
                "result_terms": {
                    "type": "array",
                    "items": {"type": "string", "enum": result_terms},
                    "description": "Applicable 結果 (result) taxonomy terms.",
                },
            },
            "required": ["cause_terms", "action_terms", "result_terms"],
        },
    }


def classify_section_text(
    client: anthropic.Anthropic,
    tool: dict,
    report_id: str,
    slug: str,
    text: str,
) -> dict:
    """Ask Claude to classify one section's text against the Mandala taxonomy.

    Uses ``tool_choice={"type": "tool", "name": CLASSIFY_TOOL_NAME}`` to
    guarantee a structured response.  A section-type hint from ``SECTION_HINTS``
    is injected as a system message so the model knows which dimensions to
    prioritise for this section type.

    @param client: Anthropic client.
    @param tool: tool definition dict from ``build_classify_tool``.
    @param report_id: failure case identifier, used only for the prompt header.
    @param slug: section slug — determines which hint to inject.
    @param text: plain-text content of the section.
    @return: dict with keys ``cause_terms``, ``action_terms``, ``result_terms``.
    """
    label = SECTIONS_INV.get(slug, slug)
    hint  = SECTION_HINTS.get(slug, "Classify any clearly evidenced terms across all three dimensions.")
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=hint,
        tools=[tool],
        tool_choice={"type": "tool", "name": CLASSIFY_TOOL_NAME},
        messages=[{
            "role": "user",
            "content": (
                f"Report: {report_id}  Section: {label}（{slug}）\n\n"
                f"{text}"
            ),
        }],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == CLASSIFY_TOOL_NAME:
            return block.input
    raise RuntimeError(
        f"classify_section tool not called for {report_id}/{slug} — unexpected API response"
    )


def load_cached_annotation(report_id: str, slug: str) -> dict | None:
    """Load a previously persisted ontology annotation from disk.

    Parses lines of the form ``[CauseType L2] 設計不良 (cause)`` written by
    ``06-export-ontology-annotations.py`` and returns a classification dict
    compatible with ``classify_section_text``.

    @param report_id: failure case identifier (e.g. ``'HA0000615'``).
    @param slug: section ASCII slug (e.g. ``'genin'``).
    @return: dict with keys ``cause_terms``, ``action_terms``, ``result_terms``,
        or ``None`` if no cache file exists.
    """
    path = os.path.join(ONTOLOGY_DIR, report_id, f"{slug}.txt")
    if not os.path.isfile(path):
        return None
    pattern = re.compile(r"^\[(?:CauseType|ActionType|ResultType) L\d+\] (.+) \((cause|action|result)\)$")
    result: dict[str, list[str]] = {"cause_terms": [], "action_terms": [], "result_terms": []}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = pattern.match(line.strip())
            if m:
                name, dimension = m.group(1), m.group(2)
                result[f"{dimension}_terms"].append(name)
    return result


def read_section_text(report_id: str, slug: str) -> str:
    """Read the plain-text content of a section from disk.

    @param report_id: failure case identifier (e.g. ``'HA0000615'``).
    @param slug: section ASCII slug (e.g. ``'genin'``).
    @return: section text, or empty string if the file is not found.
    """
    pattern = os.path.join(SECTIONS_DIR, report_id, f"*_{slug}.txt")
    matches = sorted(glob.glob(pattern))
    if not matches:
        return ""
    with open(matches[0], encoding="utf-8") as fh:
        return fh.read().strip()


def fetch_sections(session, skip_classified: bool) -> list[dict]:
    """Retrieve Section nodes to classify from Neo4j.

    @param session: active Neo4j driver session on mandara02.
    @param skip_classified: if True, exclude sections that already have a
        CLASSIFIED_AS edge.
    @return: list of dicts with keys ``report_id``, ``slug``.
    """
    if skip_classified:
        query = (
            "MATCH (s:Section)"
            " WHERE NOT (s)-[:CLASSIFIED_AS]->()"
            " RETURN s.report_id AS report_id, s.slug AS slug"
            " ORDER BY s.report_id, s.slug"
        )
    else:
        query = (
            "MATCH (s:Section)"
            " RETURN s.report_id AS report_id, s.slug AS slug"
            " ORDER BY s.report_id, s.slug"
        )
    return session.run(query).data()


def write_classified_as_edges(
    session,
    report_id: str,
    slug: str,
    classification: dict,
) -> int:
    """
    Writes CLASSIFIED_AS edges from a Section to the matching ontology nodes.

    Edges are MERGE-d so re-runs are safe.  Only ontology nodes that actually
    exist in the graph are linked (avoids dangling edges if a term is missing).

    @param session: active Neo4j driver session on mandara02.
    @param report_id: failure case identifier.
    @param slug: section ASCII slug.
    @param classification: dict with ``cause_terms``, ``action_terms``, ``result_terms``.
    @return: total number of edges written.
    """
    dim_terms: list[tuple[str, str, list[str]]] = [
        ("cause",  "CauseType",  classification.get("cause_terms", [])),
        ("action", "ActionType", classification.get("action_terms", [])),
        ("result", "ResultType", classification.get("result_terms", [])),
    ]
    n_written = 0
    for dimension, label, terms in dim_terms:
        for term in terms:
            result = session.run(
                f"MATCH (s:Section {{report_id: $report_id, slug: $slug}})"
                f" MATCH (n:{label} {{name: $term}})"
                f" MERGE (s)-[r:CLASSIFIED_AS {{dimension: $dimension}}]->(n)"
                f" RETURN count(r) AS created",
                report_id=report_id,
                slug=slug,
                term=term,
                dimension=dimension,
            ).single()
            if result:
                n_written += result["created"]
    return n_written


@click.command()
@click.option("--force", is_flag=True, default=False,
              help="Re-classify sections that already have CLASSIFIED_AS edges.")
def main(force: bool) -> None:
    """
    Classify every Section in mandara02 against the Mandala taxonomy.

    For each section, Claude is forced (via tool_choice) to pick which
    CauseType / ActionType / ResultType terms apply.  Results are written as
    CLASSIFIED_AS edges into Neo4j.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv()

    assert os.path.isdir(SECTIONS_DIR), f"Sections directory not found: {SECTIONS_DIR}"
    assert os.path.isfile(TAXONOMY_PATH), f"Taxonomy not found: {TAXONOMY_PATH}"

    taxonomy = load_taxonomy()
    tool     = build_classify_tool(taxonomy)
    client   = anthropic.Anthropic()
    driver   = GraphDatabase.driver(URI, auth=AUTH)

    try:
        with driver.session(database=DATABASE) as session:
            sections = fetch_sections(session, skip_classified=not force)
            LOG.info(
                "Sections to classify: %d%s",
                len(sections),
                " (including already-classified)" if force else " (skipping already-classified)",
            )

            n_classified = 0
            n_skipped    = 0
            n_edges      = 0

            for sec in sections:
                report_id = sec["report_id"]
                slug      = sec["slug"]

                if slug in SKIP_SLUGS:
                    LOG.debug("Skipping non-substantive section %s/%s", report_id, slug)
                    n_skipped += 1
                    continue

                text = read_section_text(report_id, slug)
                if not text:
                    LOG.warning("No text on disk for %s/%s — skipping", report_id, slug)
                    n_skipped += 1
                    continue

                cached = load_cached_annotation(report_id, slug)
                if cached is not None:
                    classification = cached
                    source = "disk"
                else:
                    classification = classify_section_text(client, tool, report_id, slug, text)
                    source = "claude"

                edges = write_classified_as_edges(session, report_id, slug, classification)
                n_edges      += edges
                n_classified += 1

                LOG.info(
                    "  [%d/%d] %s/%s [%s] → cause=%s  action=%s  result=%s  (%d edges)",
                    n_classified + n_skipped,
                    len(sections),
                    report_id,
                    slug,
                    source,
                    classification["cause_terms"],
                    classification["action_terms"],
                    classification["result_terms"],
                    edges,
                )

        LOG.info(
            "Done: %d sections classified, %d skipped (no text), %d CLASSIFIED_AS edges written",
            n_classified, n_skipped, n_edges,
        )

    finally:
        driver.close()


if __name__ == "__main__":
    main()

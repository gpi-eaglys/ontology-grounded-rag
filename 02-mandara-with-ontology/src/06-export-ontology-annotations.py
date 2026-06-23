"""
Export CLASSIFIED_AS mappings from mandara02 to disk as text files.

For every Section that has at least one CLASSIFIED_AS edge, writes a file:

    build/extract/hf-ontology/{report_id}/{slug}.txt

Each file lists the ontology categories assigned to that section, one per line,
in the same format used by the query context block:

    [CauseType L2] 設計不良 (cause)
    [ActionType L1] 点検・確認 (action)
    [ResultType L1] 機能喪失 (result)

The output directory mirrors build/extract/hf-sections/ so the two trees can
be traversed in parallel.  Existing files are overwritten.

Requirements:
    Neo4j running on bolt://localhost:7602 with mandara02 populated and
    05-annotate-ontology.py already run.

Usage:
    uv run python src/06-export-ontology-annotations.py
    uv run python src/06-export-ontology-annotations.py --out-dir /custom/path
"""
import logging
import os

import click
from neo4j import GraphDatabase

LOG = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR    = os.path.join(PRJ_DIR, "build")
DEFAULT_OUT_DIR = os.path.join(BLD_DIR, "extract", "hf-ontology")

URI      = "bolt://localhost:7602"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"


def fetch_all_annotations(session) -> dict[tuple[str, str], list[dict]]:
    """Query all CLASSIFIED_AS edges grouped by (report_id, slug).

    @param session: active Neo4j driver session on mandara02.
    @return: dict mapping (report_id, slug) to a list of ontology category dicts,
        each with keys ``category_type``, ``name``, ``level``, ``dimension``,
        ``label`` (Japanese section label).
    """
    rows = session.run(
        "MATCH (s:Section)-[:CLASSIFIED_AS]->(cat)"
        " RETURN s.report_id AS report_id, s.slug AS slug, s.label AS label,"
        "        labels(cat)[0] AS category_type, cat.name AS name,"
        "        cat.level AS level, cat.dimension AS dimension"
        " ORDER BY s.report_id, s.slug, cat.dimension, cat.level, cat.name"
    ).data()

    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row["report_id"], row["slug"])
        grouped.setdefault(key, []).append(row)
    return grouped


def format_annotation_file(label: str, slug: str, categories: list[dict]) -> str:
    """Format ontology categories as a human-readable text block.

    @param label: Japanese section label (e.g. ``'原因'``).
    @param slug: section ASCII slug (e.g. ``'genin'``).
    @param categories: list of category dicts from ``fetch_all_annotations``.
    @return: formatted file content as a string.
    """
    lines = [f"# {label}（{slug}）", ""]
    for cat in categories:
        lines.append(
            f"[{cat['category_type']} L{cat['level']}] {cat['name']} ({cat['dimension']})"
        )
    return "\n".join(lines) + "\n"


def write_annotation_file(out_dir: str, report_id: str, slug: str, content: str) -> str:
    """Write one annotation file to disk, creating parent directories as needed.

    @param out_dir: root output directory.
    @param report_id: failure case identifier (e.g. ``'HA0000615'``).
    @param slug: section ASCII slug (e.g. ``'genin'``).
    @param content: formatted file content.
    @return: absolute path of the written file.
    """
    report_dir = os.path.join(out_dir, report_id)
    os.makedirs(report_dir, exist_ok=True)
    path = os.path.join(report_dir, f"{slug}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


@click.command()
@click.option(
    "--out-dir",
    default=DEFAULT_OUT_DIR,
    show_default=True,
    help="Root directory for annotation output files.",
)
def main(out_dir: str) -> None:
    """Export all CLASSIFIED_AS ontology annotations from mandara02 to disk."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DATABASE) as session:
            LOG.info("Fetching all CLASSIFIED_AS annotations from mandara02...")
            grouped = fetch_all_annotations(session)

        LOG.info("Found annotations for %d sections", len(grouped))

        n_written = 0
        for (report_id, slug), categories in sorted(grouped.items()):
            label = categories[0]["label"] or slug
            content = format_annotation_file(label, slug, categories)
            path = write_annotation_file(out_dir, report_id, slug, content)
            LOG.info("  %s/%s → %s (%d categories)", report_id, slug, path, len(categories))
            n_written += 1

        LOG.info("Done: %d annotation files written to %s", n_written, out_dir)

    finally:
        driver.close()


if __name__ == "__main__":
    main()

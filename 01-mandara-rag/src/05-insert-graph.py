"""
Load extracted entities and relations into Neo4j.

Graph model:
    (FailureCase)-[:HAS_SECTION]->(Section)-[:MENTIONS]->(Entity)
    (Entity {type})-[:RELATION_TYPE]->(Entity)

Requirements: Neo4j running locally on bolt://localhost:7687
    docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

Usage:
    uv run python src/05-insert-graph.py
"""
import glob
import json
import logging
import os

from neo4j import GraphDatabase

from common import SECTIONS_INV

LOG = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR    = os.path.join(PRJ_DIR, "build")
RELATIONS_DIR = os.path.join(BLD_DIR, "extract", "hf-relations")
SECTIONS_DIR = os.path.join(BLD_DIR, "extract", "hf-sections")

URI  = "bolt://localhost:7687"
AUTH = ("neo4j", "password")


def insert_section(session, report_id: str, sec_slug: str, ent_rel_json: dict) -> None:
    """
    Inserts one section's entities and relations into Neo4j.

    Creates or merges a FailureCase node, a Section node linked to it,
    Entity nodes for each extracted entity, MENTIONS edges from the Section
    to each Entity, and typed relation edges between Entity pairs.

    @param session: active Neo4j driver session.
    @param report_id: identifier of the failure case report (e.g. ``'HA0000601'``).
    @param sec_slug: ASCII slug of the section (e.g. ``'genin'``), used to look up
        the kanji label via SECTIONS_INV.
    @param ent_rel_json: parsed JSON dict with ``'entities'`` and ``'relations'`` lists.
    """
    sec_label = SECTIONS_INV.get(sec_slug, sec_slug)

    session.run(
        "MERGE (c:FailureCase {id: $report_id})",
        report_id=report_id,
    )
    session.run(
        "MERGE (c:FailureCase {id: $report_id})"
        " MERGE (s:Section {report_id: $report_id, slug: $slug, label: $label})"
        " MERGE (c)-[:HAS_SECTION]->(s)",
        report_id=report_id,
        slug=sec_slug,
        label=sec_label,
    )

    for ent in ent_rel_json.get("entities", []):
        session.run(
            "MERGE (c:FailureCase {id: $report_id})"
            " MERGE (s:Section {report_id: $report_id, slug: $slug})"
            " MERGE (e:Entity {name: $name, type: $etype})"
            " MERGE (s)-[:MENTIONS]->(e)",
            report_id=report_id,
            slug=sec_slug,
            name=ent["name"],
            etype=ent["type"],
        )

    for rel in ent_rel_json.get("relations", []):
        session.run(
            "MERGE (a:Entity {name: $source})"
            " MERGE (b:Entity {name: $target})"
            " MERGE (a)-[r:" + rel["relation"] + " {report_id: $report_id, section: $slug}]->(b)",
            source=rel["source"],
            target=rel["target"],
            report_id=report_id,
            slug=sec_slug,
        )


def load_all(driver) -> None:
    """Walk the hf-relations directory and load every JSON section file.

    @param driver: Neo4j GraphDatabase driver instance.
    """
    assert os.path.isdir(RELATIONS_DIR), f"RELATIONS_DIR not found: {RELATIONS_DIR}"
    json_files = sorted(glob.glob(os.path.join(RELATIONS_DIR, "*", "*.json")))
    LOG.info(f"Found {len(json_files)} section JSON files in {RELATIONS_DIR}")

    n_inserted = 0
    with driver.session() as session:
        for fpath in json_files:
            # if not "HA0000265/05_taisaku" in fpath:
            #     continue

            report_id = os.path.basename(os.path.dirname(fpath))
            fname     = os.path.splitext(os.path.basename(fpath))[0]  # e.g. "03_genin"
            sec_slug  = fname.split("_", 1)[-1]                        # e.g. "genin"

            with open(fpath, encoding="utf-8") as fh:
                ent_rel_json = json.load(fh)

            n_inserted += 1
            LOG.info(f"Inserting ({n_inserted}) {fpath}")
            insert_section(session, report_id, sec_slug, ent_rel_json)

    LOG.info(f"Done: inserted {n_inserted:,} sections")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        load_all(driver)
    finally:
        driver.close()

"""
Load extracted entities and relations into Neo4j (mandara02).

Reads the same hf-relations build output produced by experiment 01 and
inserts it into the ``mandara02`` database, which also holds the Mandala
ontology layer.

Graph model:
    (FailureCase)-[:HAS_SECTION]->(Section)-[:MENTIONS]->(Entity)
    (Entity {type})-[:RELATION_TYPE]->(Entity)

Requirements: Neo4j running locally on bolt://localhost:7602 with mandara02 created.

Usage:
    uv run python src/03-insert-graph.py
"""
import glob
import json
import logging
import os

from neo4j import GraphDatabase

from common import SECTIONS_INV

LOG = logging.getLogger(__name__)

SCRIPT_DIR    = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR       = os.path.join(PRJ_DIR, "build")
RELATIONS_DIR = os.path.join(BLD_DIR, "extract", "hf-relations")

URI      = "bolt://localhost:7602"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"


def insert_section(session, report_id: str, sec_slug: str, ent_rel_json: dict) -> None:
    """Insert one section's entities and relations into Neo4j.

    @param session: active Neo4j driver session.
    @param report_id: identifier of the failure case report (e.g. ``'HA0000601'``).
    @param sec_slug: ASCII slug of the section (e.g. ``'genin'``).
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
    with driver.session(database=DATABASE) as session:
        for fpath in json_files:
            report_id = os.path.basename(os.path.dirname(fpath))
            fname     = os.path.splitext(os.path.basename(fpath))[0]
            sec_slug  = fname.split("_", 1)[-1]

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

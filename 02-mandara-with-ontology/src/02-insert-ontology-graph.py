"""Load the Mandala taxonomy into Neo4j as an ontology layer.

Graph model:
    (:CauseType  {name, level, group})-[:HAS_SUBCATEGORY]->(:CauseType)
    (:ActionType {name, level, group})-[:HAS_SUBCATEGORY]->(:ActionType)
    (:ResultType {name, level, group})-[:HAS_SUBCATEGORY]->(:ResultType)

Nodes are MERGE-d (idempotent — safe to re-run).

Requirements: Neo4j running on bolt://localhost:7602
    docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

Usage:
    uv run python src/02-insert-ontology-graph.py
"""

import json
import logging
import os

from neo4j import GraphDatabase

LOG = logging.getLogger(__name__)

SCRIPT_DIR    = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR       = os.path.join(PRJ_DIR, "build")
TAXONOMY_PATH = os.path.join(BLD_DIR, "mandala", "mandala_taxonomy.json")

URI      = "bolt://localhost:7602"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"

# Maps dimension key → Neo4j node label
LABELS: dict[str, str] = {
    "cause":  "CauseType",
    "action": "ActionType",
    "result": "ResultType",
}


def insert_dimension(session, dimension_key: str, label: str, items: list[dict]) -> None:
    """Insert all Level-1 and Level-2 nodes for one Mandala dimension.

    For each Level-1 item, merges the node and all its Level-2 children,
    then creates a ``HAS_SUBCATEGORY`` edge from each L1 to its L2 nodes.

    @param session: active Neo4j driver session.
    @param dimension_key: short key for the dimension (e.g. ``'cause'``).
    @param label: Neo4j node label (e.g. ``'CauseType'``).
    @param items: list of L1 item dicts from the taxonomy JSON.
    """
    for item in items:
        # Merge Level-1 node
        session.run(
            f"MERGE (n:{label} {{name: $name}})"
            " SET n.level = $level, n.group = $group, n.dimension = $dimension",
            name=item["name"],
            level=1,
            group=item["group"],
            dimension=dimension_key,
        )
        LOG.info("  L1: %s", item["name"])

        for child_name in item["children"]:
            # Merge Level-2 node
            session.run(
                f"MERGE (n:{label} {{name: $name}})"
                " SET n.level = $level, n.group = $group, n.dimension = $dimension",
                name=child_name,
                level=2,
                group=item["group"],
                dimension=dimension_key,
            )

            # Merge parent → child edge
            session.run(
                f"MATCH (parent:{label} {{name: $parent_name}})"
                f" MATCH (child:{label}  {{name: $child_name}})"
                " MERGE (parent)-[:HAS_SUBCATEGORY]->(child)",
                parent_name=item["name"],
                child_name=child_name,
            )
            LOG.info("    L2: %s", child_name)


def load_taxonomy(driver) -> None:
    """Read mandala_taxonomy.json and insert all three dimensions into Neo4j.

    @param driver: Neo4j GraphDatabase driver instance.
    """
    assert os.path.isfile(TAXONOMY_PATH), f"Taxonomy not found: {TAXONOMY_PATH}"

    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        taxonomy = json.load(f)

    with driver.session(database=DATABASE) as session:
        for dimension_key, dim_data in taxonomy.items():
            label = LABELS[dimension_key]
            items = dim_data["items"]
            l2_count = sum(len(item["children"]) for item in items)
            LOG.info(
                "Inserting %s (%s): %d L1, %d L2",
                dim_data["japanese"], label, len(items), l2_count,
            )
            insert_dimension(session, dimension_key, label, items)

    LOG.info("Done")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        load_taxonomy(driver)
    finally:
        driver.close()

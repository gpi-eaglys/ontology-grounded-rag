"""
Minimal Neo4j sample — creates a small synthetic graph and queries it.

Requirements: Neo4j running locally on bolt://localhost:7687
    docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

Usage:
    uv run python src/02-neo4j-sample.py
"""

from neo4j import GraphDatabase

URI  = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

TRIPLES = [
    ("valve",        "failed_due_to",      "metal_fatigue"),
    ("metal_fatigue","caused_by",          "high_pressure"),
    ("operator",     "ignored",            "warning_signal"),
    ("warning_signal","indicates",         "high_pressure"),
    ("maintenance",  "was_inadequate_for", "valve"),
]


def create_graph(driver):
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")  # clear previous run
        for subj, rel, obj in TRIPLES:
            s.run(
                "MERGE (a:Entity {name:$s}) "
                "MERGE (b:Entity {name:$o}) "
                "MERGE (a)-[r:REL {type:$r}]->(b)",
                s=subj, o=obj, r=rel,
            )
    print(f"Loaded {len(TRIPLES)} triples.")


def query_graph(driver):
    with driver.session() as s:
        # All triples
        print("\n--- All triples ---")
        for record in s.run("MATCH (a)-[r]->(b) RETURN a.name, r.type, b.name"):
            print(f"  ({record['a.name']}) --[{record['r.type']}]--> ({record['b.name']})")

        # What caused the valve failure?
        print("\n--- What caused the valve to fail? ---")
        for record in s.run(
            "MATCH (valve:Entity {name:'valve'})-[r]->(cause) RETURN r.type, cause.name"
        ):
            print(f"  valve --[{record['r.type']}]--> {record['cause.name']}")


if __name__ == "__main__":
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        create_graph(driver)
        query_graph(driver)
    finally:
        driver.close()

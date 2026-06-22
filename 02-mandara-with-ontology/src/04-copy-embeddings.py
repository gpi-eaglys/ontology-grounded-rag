"""
Load cached section embeddings into mandara02.

Reads .npy embedding files from ``build/extract/hf-embeddings/`` (written by
experiment 01's ``06-embed-section.py``) and stores them on the matching
Section nodes in ``mandara02``.  No OpenAI calls are made.

A vector index is created in mandara02 if it does not already exist.

Requirements: Neo4j running on bolt://localhost:7687 with mandara02 populated.
    Run 03-insert-graph.py before this script.
    Run 01's 06-embed-section.py at least once so the .npy cache exists.

Usage:
    uv run python src/04-copy-embeddings.py
"""
import glob
import logging
import os

import numpy as np
from neo4j import GraphDatabase

LOG = logging.getLogger(__name__)

SCRIPT_DIR     = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR        = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR        = os.path.join(PRJ_DIR, "build")
EMBEDDINGS_DIR = os.path.join(BLD_DIR, "extract", "hf-embeddings")

URI      = "bolt://localhost:7687"
AUTH     = ("neo4j", "password")
DATABASE = "mandara02"

EMBEDDING_DIM = 1536  # text-embedding-3-small


def ensure_vector_index(session) -> None:
    """Create the vector index on Section.embedding in mandara02 if absent.

    @param session: active Neo4j driver session on mandara02.
    """
    session.run(
        "CREATE VECTOR INDEX section_embedding IF NOT EXISTS"
        " FOR (s:Section) ON s.embedding"
        " OPTIONS {indexConfig: {"
        "   `vector.dimensions`: $dim,"
        "   `vector.similarity_function`: 'cosine'"
        " }}",
        dim=EMBEDDING_DIM,
    )


def load_embeddings() -> list[dict]:
    """Scan the .npy cache directory and load all embeddings.

    @return: list of dicts with keys ``report_id``, ``slug``, ``embedding``.
    """
    npy_files = sorted(glob.glob(os.path.join(EMBEDDINGS_DIR, "*", "*.npy")))
    LOG.info(f"Found {len(npy_files)} .npy files in {EMBEDDINGS_DIR}")
    rows = []
    for path in npy_files:
        report_id = os.path.basename(os.path.dirname(path))
        slug      = os.path.splitext(os.path.basename(path))[0]
        vector    = np.load(path).tolist()
        rows.append({"report_id": report_id, "slug": slug, "embedding": vector})
    return rows


def copy_embeddings(driver) -> None:
    """Write all cached embeddings into mandara02 Section nodes.

    @param driver: Neo4j GraphDatabase driver instance.
    """
    rows = load_embeddings()

    n_copied  = 0
    n_missing = 0
    with driver.session(database=DATABASE) as session:
        ensure_vector_index(session)
        for row in rows:
            result = session.run(
                "MATCH (s:Section {report_id: $report_id, slug: $slug})"
                " SET s.embedding = $embedding"
                " RETURN count(s) AS updated",
                report_id=row["report_id"],
                slug=row["slug"],
                embedding=row["embedding"],
            ).single()

            if result and result["updated"] > 0:
                n_copied += 1
            else:
                n_missing += 1
                LOG.warning(f"Section not found in {DATABASE}: {row['report_id']}/{row['slug']}")

    LOG.info(f"Done: copied {n_copied:,} embeddings, {n_missing} sections not found in target")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    assert os.path.isdir(EMBEDDINGS_DIR), f"Embeddings cache not found: {EMBEDDINGS_DIR} — run 01's 06-embed-section.py first"
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        copy_embeddings(driver)
    finally:
        driver.close()

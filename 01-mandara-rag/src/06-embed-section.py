"""
Embed section text and store vectors on Section nodes in Neo4j.

For each Section node that has no embedding yet, reads the corresponding
.txt file, calls the OpenAI embeddings API, and stores the vector as the
``embedding`` property.  A vector index is created if it does not exist.

Embeddings are cached to disk as .npy files under
``build/extract/hf-embeddings/<report_id>/<slug>.npy`` so that re-runs and
DB rebuilds never call OpenAI for a section that was already embedded.

Requirements:
    OPENAI_API_KEY env var set
    Neo4j running on bolt://localhost:7687

Usage:
    uv run python src/06-embed-section.py
"""
import glob
import logging
import os

import numpy as np
import openai
from neo4j import GraphDatabase

LOG = logging.getLogger(__name__)

SCRIPT_DIR      = os.path.dirname(os.path.realpath(__file__))
PRJ_DIR         = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BLD_DIR         = os.path.join(PRJ_DIR, "build")
SECTIONS_DIR    = os.path.join(BLD_DIR, "extract", "hf-sections")
EMBEDDINGS_DIR  = os.path.join(BLD_DIR, "extract", "hf-embeddings")

URI      = "bolt://localhost:7687"
AUTH     = ("neo4j", "password")
DATABASE = "mandara01"

OPENAI_MODEL  = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # text-embedding-3-small output dimension


def ensure_vector_index(session) -> None:
    """Create the vector index on Section.embedding if it does not exist.

    @param session: active Neo4j driver session.
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


def cache_path(report_id: str, slug: str) -> str:
    """Return the .npy cache path for a section embedding.

    @param report_id: failure case identifier (e.g. ``'HA0000615'``).
    @param slug: section ASCII slug (e.g. ``'keika'``).
    @return: absolute path to the .npy file.
    """
    return os.path.join(EMBEDDINGS_DIR, report_id, f"{slug}.npy")


def load_cached(report_id: str, slug: str) -> list[float] | None:
    """Load a cached embedding from disk if it exists.

    @param report_id: failure case identifier.
    @param slug: section ASCII slug.
    @return: embedding as a list of floats, or ``None`` if not cached.
    """
    path = cache_path(report_id, slug)
    if os.path.isfile(path):
        return np.load(path).tolist()
    return None


def save_cache(report_id: str, slug: str, vector: list[float]) -> None:
    """Persist an embedding vector to disk as a .npy file.

    @param report_id: failure case identifier.
    @param slug: section ASCII slug.
    @param vector: embedding as a list of floats.
    """
    path = cache_path(report_id, slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.save(path, np.array(vector, dtype=np.float32))


def embed_all(driver, oa: openai.OpenAI) -> None:
    """Embed every Section node that has no embedding yet.

    For each section, checks the .npy disk cache first.  Only calls OpenAI
    when no cached vector exists.  Writes the vector to both the cache and
    Neo4j.

    @param driver: Neo4j GraphDatabase driver instance.
    @param oa: OpenAI client instance.
    """
    with driver.session(database=DATABASE) as session:
        ensure_vector_index(session)
        rows = session.run(
            "MATCH (s:Section) WHERE s.embedding IS NULL"
            " RETURN s.report_id AS report_id, s.slug AS slug"
        ).data()

    n = len(rows)
    LOG.info(f"Found {n} sections to embed")

    ix_row = 0
    for row in rows:
        report_id = row["report_id"]
        slug      = row["slug"]
        ix_row   += 1

        vector = load_cached(report_id, slug)
        if vector is not None:
            LOG.info(f"Cache hit ({ix_row}/{n}) {report_id}/{slug}")
        else:
            pattern = os.path.join(SECTIONS_DIR, report_id, f"*_{slug}.txt")
            matches = sorted(glob.glob(pattern))
            if not matches:
                LOG.warning(f"No text file found for ({ix_row}/{n}) {report_id}/{slug}, skipping")
                continue

            with open(matches[0], encoding="utf-8") as fh:
                text = fh.read().strip()

            if not text:
                LOG.warning(f"Empty text for ({ix_row}/{n}) {report_id}/{slug}, skipping")
                continue

            LOG.info(f"Embedding ({ix_row}/{n}) {report_id}/{slug}")
            vector = oa.embeddings.create(input=text, model=OPENAI_MODEL).data[0].embedding
            save_cache(report_id, slug, vector)

        with driver.session(database=DATABASE) as session:
            session.run(
                "MATCH (s:Section {report_id: $report_id, slug: $slug})"
                " SET s.embedding = $embedding",
                report_id=report_id,
                slug=slug,
                embedding=vector,
            )

    LOG.info("Done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(message)s", datefmt="%H:%M:%S")

    assert os.path.isdir(SECTIONS_DIR), f"Cannot find root dir for sections: {SECTIONS_DIR}"

    from dotenv import load_dotenv
    load_dotenv()

    oa     = openai.OpenAI()  # requires 'OPENAI_API_KEY' env var
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        embed_all(driver, oa)
    finally:
        driver.close()

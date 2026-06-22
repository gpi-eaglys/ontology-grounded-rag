#! /usr/bin/env bash

# Starts Neo4j with two experiment databases:
#   mandara01  — baseline (no ontology)
#   mandara02  — ontology-grounded
#
# First-time setup: after the container is running, create the databases once:
#   docker exec -it neo4j cypher-shell -u neo4j -p password \
#     "CREATE DATABASE mandara01 IF NOT EXISTS; CREATE DATABASE mandara02 IF NOT EXISTS;"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR=$(realpath "${SCRIPT_DIR}/..")
NEO4J_DATA_DIR="${REPO_DIR}/build/neo4j-db"

echo "[INFO]  Using data dir: $NEO4J_DATA_DIR"

docker run --name neo4j --rm \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=eval \
  -v "${NEO4J_DATA_DIR}"/neo4j/data:/data \
  neo4j:enterprise


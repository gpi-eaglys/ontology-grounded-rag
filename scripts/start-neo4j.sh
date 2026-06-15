#! /usr/bin/env bash 

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR=$(realpath "${SCRIPT_DIR}/../..")
NEO4J_DATA_DIR="${REPO_DIR}/build/neo4j-db"

echo "[INFO]  Using data dir: $NEO4J_DATA_DIR"

docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v "${NEO4J_DATA_DIR}"/neo4j/data:/data \
  neo4j:latest


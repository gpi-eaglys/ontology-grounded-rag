#! /usr/bin/env bash
# Starts Neo4j for experiment 03 (causal chain knowledge graph).
#
# Browser:  http://localhost:7403   (user: neo4j  /  password: password)
# Bolt:     bolt://localhost:7603
#
# After starting, populate the graph:
#   uv run --project 03-fuse python3 03-fuse/src/01-build-graph.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker compose -f "${SCRIPT_DIR}/../docker-compose.yml" up -d neo4j-exp03

echo "[INFO]  Neo4j exp03 is running."
echo "[INFO]  Browser: http://localhost:7403  (neo4j / password)"
echo "[INFO]  Bolt:    bolt://localhost:7603"

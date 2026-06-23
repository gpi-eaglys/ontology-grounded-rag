#!/usr/bin/env bash
# Migrate mandara01 and mandara02 from the running enterprise Neo4j container
# into two separate Community containers (neo4j-exp01, neo4j-exp02).
#
# Prerequisites:
#   - The enterprise container named 'neo4j' must be running
#   - docker compose must be available in the project root
#
# After migration, update DATABASE in scripts:
#   01-mandara-rag     -> "neo4j"  (was "mandara01")
#   02-mandara-with-ontology -> "neo4j"  (was "mandara02")
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(realpath "${SCRIPT_DIR}/..")"
DUMPS_DIR="${REPO_DIR}/build/neo4j-db/neo4j/data/dumps"

echo "==> [1/6] Creating dumps directory..."
docker exec neo4j mkdir -p /data/dumps

echo "==> [2/6] Stopping mandara01 and mandara02 for consistent dump..."
docker exec neo4j cypher-shell -u neo4j -p password "STOP DATABASE mandara01;"
docker exec neo4j cypher-shell -u neo4j -p password "STOP DATABASE mandara02;"

echo "==> [3/6] Dumping databases..."
docker exec neo4j neo4j-admin database dump mandara01 --to-path=/data/dumps/
docker exec neo4j neo4j-admin database dump mandara02 --to-path=/data/dumps/
echo "    Dumps written to: ${DUMPS_DIR}/"

echo "==> Restarting databases in enterprise container..."
docker exec neo4j cypher-shell -u neo4j -p password "START DATABASE mandara01;"
docker exec neo4j cypher-shell -u neo4j -p password "START DATABASE mandara02;"

echo "==> [4/6] Starting Community containers..."
(cd "${REPO_DIR}" && docker compose up -d neo4j-exp01 neo4j-exp02)

echo "    Waiting 20s for containers to initialize..."
sleep 20

echo "==> [5/6] Loading mandara01 into neo4j-exp01..."
# neo4j-admin database load looks for a file named <database>.dump in --from-path
docker cp "${DUMPS_DIR}/mandara01.dump" neo4j-exp01:/var/lib/neo4j/neo4j.dump
docker exec neo4j-exp01 cypher-shell -u neo4j -p password "STOP DATABASE neo4j;"
docker exec neo4j-exp01 neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/ --overwrite-destination
docker exec neo4j-exp01 cypher-shell -u neo4j -p password "START DATABASE neo4j;"
echo "    neo4j-exp01 ready at bolt://localhost:7601"

echo "==> [6/6] Loading mandara02 into neo4j-exp02..."
docker cp "${DUMPS_DIR}/mandara02.dump" neo4j-exp02:/var/lib/neo4j/neo4j.dump
docker exec neo4j-exp02 cypher-shell -u neo4j -p password "STOP DATABASE neo4j;"
docker exec neo4j-exp02 neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/ --overwrite-destination
docker exec neo4j-exp02 cypher-shell -u neo4j -p password "START DATABASE neo4j;"
echo "    neo4j-exp02 ready at bolt://localhost:7602"

echo ""
echo "Migration complete."
echo "Next steps:"
echo "  1. Update DATABASE = 'neo4j' in all scripts (was 'mandara01'/'mandara02')"
echo "  2. Stop the enterprise container: docker stop neo4j"
echo "  3. Verify: docker compose ps"

#! /usr/bin/env bash 

# crawls mandala file 

set -e

PY_SCRIPT="src/01-crawl-site.py"

# TARGET_URL_ROOT="https://www.shippai.org/fkd/inf/mandara.html"
TARGET_URL_ROOT="https://www.shippai.org/fkd/index.php"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
UV_DIR=$(realpath ${SCRIPT_DIR}/..)
REPO_DIR=$(realpath ${SCRIPT_DIR}/../..)

echo $REPO_DIR 
CRAWL_DUMP_DIR="${REPO_DIR}/build/mandala/crawl/"
mkdir -p "${CRAWL_DUMP_DIR}"
echo "[INFO]  Python script : ${PY_SCRIPT}"
echo "[INFO]  Crawl root URL: ${TARGET_URL_ROOT}"
echo "[INFO]  Crawl dump dir: ${CRAWL_DUMP_DIR}"

if [[ ! -f "${UV_DIR}/${PY_SCRIPT}" ]]; then
    echo "[ERROR]  Failed to find python script: ${UV_DIR}/${PY_SCRIPT}"
    exit 1
fi

pushd $UV_DIR > /dev/null

uv run python ${PY_SCRIPT} -o ${CRAWL_DUMP_DIR} $TARGET_URL_ROOT

popd > /dev/null




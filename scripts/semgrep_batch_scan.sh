#!/bin/bash
# Batch semgrep static scan
SRC_ROOT="./source_code"
RULE_ROOT="./rules"
OUTPUT_ROOT="./audit_output"

mkdir -p ${OUTPUT_ROOT}

for dir in ${SRC_ROOT}/*/
do
    repo_name=$(basename ${dir%/})
    echo "======================================"
    echo "[SCAN] Start scan: ${repo_name}"
    semgrep scan \
        --config ${RULE_ROOT}/php \
        --config ${RULE_ROOT}/java \
        --json \
        -o ${OUTPUT_ROOT}/${repo_name}.json \
        ${dir}
    echo "[DONE] Report saved to ${OUTPUT_ROOT}/${repo_name}.json"
done

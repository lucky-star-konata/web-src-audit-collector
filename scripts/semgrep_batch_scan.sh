#!/bin/bash
# semgrep batch scan script
SRC_DIR="./source_code"
OUTPUT_DIR="./audit_output"
PHP_RULE="./rules/php/basic-php-vuln.yaml"
JAVA_RULE="./rules/java/basic-java-vuln.yaml"

# 前置检查
if ! command -v semgrep &> /dev/null
then
    echo "[!] semgrep not found, please install semgrep first."
    exit 1
fi

if [ ! -d "${SRC_DIR}" ];then
    echo "[!] ${SRC_DIR} not found, run batch_clone.py first!"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

for project in "${SRC_DIR}"/*/
do
    [ -d "${project}" ] || continue
    project_name=$(basename "${project}")
    echo -e "\n[+] Start scanning project: ${project_name}"

    # 统计php和java文件数量，智能判断项目类型
    PHP_COUNT=$(find "${project}" -type f -name "*.php" | wc -l | tr -d ' ')
    JAVA_COUNT=$(find "${project}" -type f -name "*.java" | wc -l | tr -d ' ')

    if [ "${PHP_COUNT}" -gt 0 ];then
        echo "[*] Detected PHP project (${PHP_COUNT} files), use php rules"
        semgrep scan --config "${PHP_RULE}" --json "${project}" > "${OUTPUT_DIR}/${project_name}_php_report.json"
    elif [ "${JAVA_COUNT}" -gt 0 ];then
        echo "[*] Detected Java project (${JAVA_COUNT} files), use java rules"
        semgrep scan --config "${JAVA_RULE}" --json "${project}" > "${OUTPUT_DIR}/${project_name}_java_report.json"
    else
        echo "[!] Cannot identify language, skip ${project_name}"
    fi
done

echo -e "\n[+] All scan finished, reports saved in ${OUTPUT_DIR}"

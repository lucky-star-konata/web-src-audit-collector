#!/bin/bash
# semgrep batch scan script
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

SRC_DIR="${ROOT_DIR}/source_code"
OUTPUT_DIR="${ROOT_DIR}/audit_output"
PHP_RULE="${ROOT_DIR}/rules/php/basic-php-vuln.yaml"
JAVA_RULE="${ROOT_DIR}/rules/java/basic-java-vuln.yaml"

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

# 公共扫描参数：关闭指标上报与版本检查，避免受限网络下卡住；保持规则 ID 与文档一致
SEMGREP_OPTS=(--metrics off --disable-version-check --no-rewrite-rule-ids)

found=0
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
        semgrep scan "${SEMGREP_OPTS[@]}" --config "${PHP_RULE}" --json "${project}" > "${OUTPUT_DIR}/${project_name}_php_report.json"
        found=$((found + 1))
    elif [ "${JAVA_COUNT}" -gt 0 ];then
        echo "[*] Detected Java project (${JAVA_COUNT} files), use java rules"
        semgrep scan "${SEMGREP_OPTS[@]}" --config "${JAVA_RULE}" --json "${project}" > "${OUTPUT_DIR}/${project_name}_java_report.json"
        found=$((found + 1))
    else
        echo "[!] Cannot identify language, skip ${project_name}"
    fi
done

if [ "${found}" -eq 0 ];then
    echo -e "\n[!] No scannable project found under ${SRC_DIR}"
    exit 0
fi

echo -e "\n[+] All scan finished, reports saved in ${OUTPUT_DIR}"
echo "[+] Generate summary: python3 ${SCRIPT_DIR}/summary_report.py"

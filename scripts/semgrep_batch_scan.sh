#!/bin/bash
# semgrep batch scan script
set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

SRC_DIR="${ROOT_DIR}/source_code"
OUTPUT_DIR="${ROOT_DIR}/audit_output"
RULES_DIR="${ROOT_DIR}/rules"
VERSION_FILE="${ROOT_DIR}/VERSION"

KEEP_STALE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --keep-stale) KEEP_STALE=1 ;;
        --version)
            if [ -f "${VERSION_FILE}" ]; then cat "${VERSION_FILE}"; else echo "0.0.0"; fi
            exit 0
            ;;
        -h|--help)
            echo "Usage: bash scripts/semgrep_batch_scan.sh [--keep-stale] [--version]"
            echo "  --keep-stale  保留 source_code 中已不存在项目的旧报告"
            exit 0
            ;;
        *)
            echo "[!] Unknown argument: $1"
            exit 2
            ;;
    esac
    shift
done

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

if [ ! -d "${RULES_DIR}" ];then
    echo "[!] ${RULES_DIR} not found!"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# 公共扫描参数：关闭指标上报与版本检查，避免受限网络下卡住；保持规则 ID 与文档一致；
# 排除第三方依赖目录与 .git，降低噪声与重复命中
SEMGREP_OPTS=(--metrics off --disable-version-check --no-rewrite-rule-ids
              --timeout 60 --exclude vendor --exclude node_modules --exclude .git)

count_files() {
    find "$1" -type f -name "$2" \
        -not -path '*/vendor/*' -not -path '*/node_modules/*' -not -path '*/.git/*' \
        | wc -l | tr -d ' '
}

# 规则按语言目录加载：rules/<语言>/ 下新增 yaml 无需改脚本即可生效
scan_language() {
    local project_path="$1"
    local project_name="$2"
    local language="$3"
    local file_count="$4"
    local rule_dir="${RULES_DIR}/${language}"
    local report="${OUTPUT_DIR}/${project_name}_${language}_report.json"
    local tmp="${report}.tmp"

    if [ ! -d "${rule_dir}" ]; then
        echo "[!] Rule directory missing: ${rule_dir}, skip ${language} for ${project_name}"
        return 2
    fi

    echo "[*] Detected ${language} (${file_count} files), scanning ..."
    if semgrep scan "${SEMGREP_OPTS[@]}" --config "${rule_dir}" --json "${project_path}" > "${tmp}" \
        && [ -s "${tmp}" ] && grep -q '"results"' "${tmp}"; then
        mv "${tmp}" "${report}"
        echo "[OK] ${report}"
        return 0
    fi

    rm -f "${tmp}"
    rm -f "${report}"
    echo "[FAIL] semgrep failed or produced invalid JSON for ${project_name} (${language})"
    return 1
}

# 清理已从 source_code 移除项目的旧报告，避免污染 summary / triage
pruned=0
if [ "${KEEP_STALE}" -eq 0 ]; then
    for report in "${OUTPUT_DIR}"/*_report.json; do
        [ -e "${report}" ] || continue
        base="$(basename "${report}")"
        stem="${base%_report.json}"
        project="${stem%_php}"
        if [ "${project}" = "${stem}" ]; then
            project="${stem%_java}"
        fi
        if [ -d "${SRC_DIR}/${project}" ]; then
            continue
        fi
        rm -f "${report}"
        pruned=$((pruned + 1))
    done
fi

scanned=0
failed=0
skipped=0

for project in "${SRC_DIR}"/*/
do
    [ -d "${project}" ] || continue
    project="${project%/}"
    project_name=$(basename "${project}")
    echo -e "\n[+] Start scanning project: ${project_name}"

    PHP_COUNT=$(count_files "${project}" "*.php")
    JAVA_COUNT=$(count_files "${project}" "*.java")

    if [ "${PHP_COUNT}" -eq 0 ] && [ "${JAVA_COUNT}" -eq 0 ]; then
        echo "[!] Cannot identify language, skip ${project_name}"
        skipped=$((skipped + 1))
        continue
    fi

    # 同一项目可同时含多种语言，分别输出报告
    if [ "${PHP_COUNT}" -gt 0 ]; then
        scan_language "${project}" "${project_name}" "php" "${PHP_COUNT}"
        case $? in
            0) scanned=$((scanned + 1)) ;;
            1) failed=$((failed + 1)) ;;
        esac
    fi

    if [ "${JAVA_COUNT}" -gt 0 ]; then
        scan_language "${project}" "${project_name}" "java" "${JAVA_COUNT}"
        case $? in
            0) scanned=$((scanned + 1)) ;;
            1) failed=$((failed + 1)) ;;
        esac
    fi
done

echo -e "\n[FINISH] scanned=${scanned} failed=${failed} skipped=${skipped} pruned_stale=${pruned}"

if [ "${scanned}" -eq 0 ] && [ "${failed}" -eq 0 ]; then
    echo -e "[!] No scannable project found under ${SRC_DIR}"
    exit 0
fi

echo "[+] All scan finished, reports saved in ${OUTPUT_DIR}"
echo "[+] Generate summary: python3 ${SCRIPT_DIR}/summary_report.py"
echo "[+] Run triage: python3 ${SCRIPT_DIR}/triage_report.py"

if [ "${failed}" -gt 0 ]; then
    exit 1
fi
exit 0

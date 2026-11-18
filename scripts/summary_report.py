import argparse
import json
import sys
from collections import Counter
from datetime import datetime

from utils import OUTPUT_ROOT, VERSION, project_relative

SEVERITY_ORDER = ["ERROR", "WARNING", "INFO"]
MAX_FINDINGS_PER_PROJECT = 200


def parse_report_name(path):
    """从 `<项目>_<语言>_report.json` 拆出项目名与语言"""
    stem = path.stem
    if stem.endswith("_report"):
        stem = stem[: -len("_report")]
    for suffix in ("_php", "_java"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)], suffix[1:]
    return stem, "unknown"


def load_reports():
    """读取 audit_output 下的 semgrep JSON 报告"""
    reports = []
    for path in sorted(OUTPUT_ROOT.glob("*_report.json")):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Skip {path.name}: {e}", file=sys.stderr)
            continue

        results = data.get("results") or []
        stats = Counter(r.get("extra", {}).get("severity", "INFO") for r in results)
        name, language = parse_report_name(path)
        reports.append({
            "name": name,
            "language": language,
            "file": path.name,
            "results": results,
            "stats": stats,
        })
    return reports


def build_markdown(reports):
    total = sum(len(r["results"]) for r in reports)
    project_count = len({r["name"] for r in reports})
    lines = [
        "# 扫描汇总报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 项目数：{project_count}（报告 {len(reports)} 份，按语言拆分）",
        f"- 命中总数：{total}",
        "",
        "## 项目概览",
        "",
        "| 项目 | 语言 | ERROR | WARNING | INFO | 合计 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in reports:
        s = r["stats"]
        lines.append(
            f"| {r['name']} | {r['language']} | {s.get('ERROR', 0)} | {s.get('WARNING', 0)} "
            f"| {s.get('INFO', 0)} | {len(r['results'])} |"
        )

    rule_counter = Counter()
    for r in reports:
        for item in r["results"]:
            rule_counter[item.get("check_id", "unknown")] += 1

    if rule_counter:
        lines += ["", "## 规则命中排行", "", "| 规则 | 命中次数 |", "| --- | ---: |"]
        for rule, count in rule_counter.most_common(20):
            lines.append(f"| `{rule}` | {count} |")

    lines += ["", "## 明细", ""]
    for r in reports:
        if not r["results"]:
            continue
        lines.append(f"### {r['name']}（{r['language']}）")
        lines.append("")
        shown = r["results"][:MAX_FINDINGS_PER_PROJECT]
        for item in shown:
            sev = item.get("extra", {}).get("severity", "INFO")
            msg = item.get("extra", {}).get("message", "").strip().replace("\n", " ")
            rel_path = project_relative(item.get("path", ""), r["name"])
            line = (item.get("start") or {}).get("line")
            lines.append(
                f"- **[{sev}]** `{rel_path}:{line}` "
                f"`{item.get('check_id')}` — {msg}"
            )
        if len(r["results"]) > len(shown):
            lines.append(f"- ... 另有 {len(r['results']) - len(shown)} 条未展示")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="把 semgrep JSON 报告汇总为 Markdown")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.parse_args()

    reports = load_reports()
    if not reports:
        print(f"[!] No report found in {OUTPUT_ROOT}, run semgrep_batch_scan.sh first.")
        return 1

    markdown = build_markdown(reports)
    out = OUTPUT_ROOT / "summary.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"[OK] Summary written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""扫描结果收敛：去重、排除第三方目录、白名单过滤、基线对比，输出待人工 triage 的清单。

用法：
    python3 scripts/triage_report.py
    python3 scripts/triage_report.py --baseline audit_output/baseline
    python3 scripts/triage_report.py --whitelist triage_whitelist.txt --top 500
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from utils import OUTPUT_ROOT, VERSION, project_relative

# 严重级排序，数字越小越优先
SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}

# 默认排除的第三方 / 测试目录，避免 vendor 噪声淹没真实入口
DEFAULT_EXCLUDES = [
    "/vendor/",
    "/node_modules/",
    "/target/",
    "/tests/",
    "/test/",
    "/third_party/",
    "/static/lib/",
]


def load_whitelist(path):
    """白名单格式：每行 `规则ID` 或 `规则ID|路径子串`，`#` 开头为注释"""
    entries = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rule, _, subpath = line.partition("|")
            entries.append((rule.strip(), subpath.strip() or None))
    return entries


def is_whitelisted(finding, entries):
    """规则 ID 精确匹配（`*` 表示任意规则），路径为子串匹配"""
    for rule, subpath in entries:
        if rule not in ("*", finding["check_id"]):
            continue
        if subpath is None or subpath in finding["rel_path"]:
            return True
    return False


def report_project_name(path):
    """从 `<项目>_<语言>_report.json` 中还原项目名"""
    name = path.stem[: -len("_report")]
    for suffix in ("_php", "_java"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def load_findings(report_dir):
    """读取目录下 semgrep JSON 报告，统一为内部结构"""
    findings = []
    for path in sorted(report_dir.glob("*_report.json")):
        project = report_project_name(path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Skip {path.name}: {e}", file=sys.stderr)
            continue

        for item in data.get("results") or []:
            extra = item.get("extra") or {}
            raw_path = item.get("path") or ""
            findings.append({
                "project": project,
                "check_id": item.get("check_id") or "unknown",
                "severity": extra.get("severity", "INFO"),
                "message": (extra.get("message") or "").strip().replace("\n", " "),
                "rel_path": project_relative(raw_path, project),
                "line": (item.get("start") or {}).get("line") or 0,
            })
    return findings


def main():
    parser = argparse.ArgumentParser(description="收敛 semgrep 扫描结果，生成 triage 清单")
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT), help="报告目录，默认 audit_output")
    parser.add_argument("--baseline", help="基线报告目录，只保留基线中不存在的新增命中")
    parser.add_argument("--whitelist", help="白名单文件：规则ID 或 规则ID|路径子串")
    parser.add_argument("--extra-exclude", action="append", default=[], help="额外排除的路径子串，可多次指定")
    parser.add_argument("--no-default-exclude", action="store_true", help="不启用默认第三方目录排除")
    parser.add_argument("--top", type=int, default=300, help="待判定清单最多展示条数，默认 300")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    findings = load_findings(output_dir)
    if not findings:
        print(f"[!] No report found in {output_dir}, run semgrep_batch_scan.sh first.")
        return 1

    raw_total = len(findings)
    excludes = ([] if args.no_default_exclude else DEFAULT_EXCLUDES) + args.extra_exclude
    findings = [f for f in findings if not any(p in "/" + f["rel_path"] for p in excludes)]
    excluded = raw_total - len(findings)

    # 同规则、同文件、同行视为同一条命中（多规则集扫描时可能重复输出）
    after_exclude = len(findings)
    deduped = {}
    for f in findings:
        key = (f["project"], f["check_id"], f["rel_path"], f["line"])
        deduped.setdefault(key, f)
    findings = list(deduped.values())
    deduplicated = after_exclude - len(findings)

    whitelisted = 0
    if args.whitelist:
        entries = load_whitelist(args.whitelist)
        before = len(findings)
        findings = [f for f in findings if not is_whitelisted(f, entries)]
        whitelisted = before - len(findings)

    baseline_suppressed = 0
    if args.baseline:
        baseline_keys = {
            (f["project"], f["check_id"], f["rel_path"], f["line"])
            for f in load_findings(Path(args.baseline))
        }
        before = len(findings)
        findings = [
            f for f in findings
            if (f["project"], f["check_id"], f["rel_path"], f["line"]) not in baseline_keys
        ]
        baseline_suppressed = before - len(findings)

    findings.sort(key=lambda f: (
        SEVERITY_ORDER.get(f["severity"], 9),
        f["project"].lower(),
        f["check_id"],
        f["rel_path"],
        f["line"],
    ))

    rule_counter = Counter((f["project"], f["check_id"]) for f in findings)
    sev_counter = Counter(f["severity"] for f in findings)

    lines = [
        "# Triage 清单",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 原始命中：{raw_total}",
        f"- 排除第三方/测试目录：{excluded}",
        f"- 去重：{deduplicated}",
        f"- 白名单过滤：{whitelisted}",
        f"- 基线抑制：{baseline_suppressed}",
        f"- 剩余待判定：{len(findings)}（ERROR {sev_counter.get('ERROR', 0)} / "
        f"WARNING {sev_counter.get('WARNING', 0)} / INFO {sev_counter.get('INFO', 0)}）",
        "",
    ]

    if not findings:
        lines += ["当前无新增命中。", ""]
    else:
        lines += [
            "## 命中分布（项目 × 规则）",
            "",
            "| 项目 | 规则 | 数量 |",
            "| --- | --- | ---: |",
        ]
        for (project, rule), count in rule_counter.most_common(30):
            lines.append(f"| {project} | `{rule}` | {count} |")

        lines += [
            "",
            "## 待判定清单",
            "",
            "判定方法：入口是否对外 → 参数是否可控 → sink 前是否有效过滤，三问全 Yes 才升级为疑似真洞。",
            "",
            "| # | 项目 | 级别 | 规则 | 位置 | 说明 | 入口对外 | 参数可控 | 有效过滤 | 结论 | 备注 |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for idx, f in enumerate(findings[: args.top], 1):
            msg = f["message"].replace("|", "\\|")
            lines.append(
                f"| {idx} | {f['project']} | {f['severity']} | `{f['check_id']}` "
                f"| `{f['rel_path']}:{f['line']}` | {msg} | ? | ? | ? | 待判定 |  |"
            )
        if len(findings) > args.top:
            lines.append("")
            lines.append(f"> 另有 {len(findings) - args.top} 条未展示，可用 `--top` 调整。")

    markdown = "\n".join(lines).rstrip() + "\n"
    md_path = output_dir / "triage.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # 机器可读结果，便于后续脚本或人工标注后回流白名单
    json_path = output_dir / "triage.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "raw_total": raw_total,
                "excluded": excluded,
                "deduplicated": deduplicated,
                "whitelisted": whitelisted,
                "baseline_suppressed": baseline_suppressed,
                "remaining": len(findings),
            },
            "findings": findings,
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(findings)} findings left, written to {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

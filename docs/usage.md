# 使用说明

本文档覆盖从环境准备到报告解读的完整流程。所有命令都请在**仓库根目录**执行，保证 `source_code/`、`audit_output/` 落在顶层。

## 1. 环境准备

```bash
git clone https://github.com/lucky-star-konata/web-src-audit-collector.git
cd web-src-audit-collector
python3 -m pip install semgrep
```

| 组件 | 检查命令 | 期望结果 |
| --- | --- | --- |
| git | `git --version` | 输出 git 版本号 |
| python | `python3 --version` | >= 3.8 |
| semgrep | `semgrep --version` | 输出版本号 |

> Windows 用户：`.sh` 脚本需在 WSL 或 Git Bash 中运行；`python3` 可为 `python`。

## 2. 配置目标仓库 `repo_list.txt`

一行一个 git 地址，`#` 开头为注释：

```
# Open-source Web Projects for Code Audit
https://mirror.ghproxy.com/https://github.com/easysoft/zentaopms.git
https://mirror.ghproxy.com/https://github.com/emlog/emlog.git
```

- 建议加镜像前缀（`https://mirror.ghproxy.com/`），避免直连 GitHub 超时或被限速。
- 地址必须以 `.git` 结尾或能被 `git clone` 直接识别。

## 3. 批量克隆 `scripts/batch_clone.py`

```bash
python3 scripts/batch_clone.py
```

行为说明：

- 读取 `repo_list.txt`，逐行克隆到 `source_code/<仓库名>/`
- 目标目录已存在则打印 `[SKIP]` 跳过，不会重复下载
- 单仓库克隆超时 300 秒；失败会打印 `[FAIL]` 并计入末尾汇总
- 结束后输出成功 / 跳过 / 失败数量统计

产物：

```
source_code/
├── zentaopms/
├── emlog/
└── JeecgBoot/
```

## 4. 批量扫描 `scripts/semgrep_batch_scan.sh`

```bash
bash scripts/semgrep_batch_scan.sh
```

行为说明：

1. 前置检查：`semgrep` 是否存在、`source_code/` 是否存在
2. 遍历 `source_code/` 下每个项目，统计 `.php` 与 `.java` 文件数量
3. 命中 PHP → 使用 `rules/php/basic-php-vuln.yaml`；否则命中 Java → 使用 `rules/java/basic-java-vuln.yaml`
4. 两类都没有 → 跳过该项目

产物：

```
audit_output/
├── zentaopms_php_report.json
├── emlog_php_report.json
└── JeecgBoot_java_report.json
```

> 注意：语言判定是「PHP 优先」。若项目同时含 PHP 与 Java，只会生成 PHP 报告；需要两者都扫时，把脚本中的 `elif` 改为两个独立 `if`。

## 5. 解读报告

报告是标准 Semgrep JSON，关键字段在 `results[]`：`check_id`（规则 ID）、`path`、`start.line`、`extra.message`。

```bash
# 每个规则的命中数量
jq -r '.results[] | .check_id' audit_output/*.json | sort | uniq -c | sort -rn

# 列出所有命中的文件与行号
jq -r '.results[] | "\(.path):\(.start.line) [\(.check_id)]"' audit_output/*.json
```

## 6. 清理本地源码 `scripts/clean_source.sh`

```bash
bash scripts/clean_source.sh
```

会二次确认后清空 `source_code/*`，保留 `audit_output/`。

## 7. 自定义规则

1. 在 `rules/<语言>/` 下新建 yaml（参考现有文件格式）：

```yaml
rules:
  - id: php-file-include
    pattern: include($VAR)
    message: 变量直接进入 include，可能存在本地文件包含
    languages: [php]
    severity: WARNING
```

2. 在 `semgrep_batch_scan.sh` 顶部把对应变量指向新文件，或直接改成扫描整个 `rules/` 目录：

```bash
semgrep scan --config rules --json "${project}" > "${OUTPUT_DIR}/${project_name}_report.json"
```

## 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 克隆超时 / Connection reset | 直连 GitHub 被限速 | 使用 `ghproxy` 等镜像前缀；或配置代理 |
| `semgrep not found` | 未安装 / 不在 PATH | `python3 -m pip install semgrep` 后重试 |
| `source_code not found` | 未先克隆 | 先执行 `batch_clone.py` |
| 项目被跳过，无报告 | 未识别到 php / java 文件 | 确认目录结构，或按需扩展语言判定 |
| `import utils` 报错 | 工作目录不对 | 在仓库根目录用 `python3 scripts/batch_clone.py` 运行 |

## 免责声明

本工具仅用于授权范围内的安全学习，请遵守 [DISCLAIMER.md](../DISCLAIMER.md)。

# 使用说明

本文档覆盖从环境准备到报告解读的完整流程。脚本以**仓库根目录**为基准解析路径，因此在任意目录执行都可正常工作。

## 1. 环境准备

```bash
git clone https://github.com/lucky-star-konata/web-src-audit-collector.git
cd web-src-audit-collector
python3 -m pip install -r requirements.txt
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

## 5. 生成汇总 `scripts/summary_report.py`

```bash
python3 scripts/summary_report.py
```

读取 `audit_output/*_report.json`，输出 `audit_output/summary.md`，包含：

- 项目概览表（各等级命中数）
- 规则命中排行（Top 20）
- 每个项目的命中明细（`路径:行号` + 规则 ID + 说明，单项目最多展示 200 条）

单个报告 JSON 损坏时会打印 `[WARN]` 并跳过，不影响其余报告。

## 6. 解读报告

报告是标准 Semgrep JSON，关键字段在 `results[]`：`check_id`（规则 ID）、`path`、`start.line`、`extra.message`、`extra.severity`。

```bash
# 每个规则的命中数量
jq -r '.results[] | .check_id' audit_output/*.json | sort | uniq -c | sort -rn

# 列出所有命中的文件与行号
jq -r '.results[] | "\(.path):\(.start.line) [\(.check_id)]"' audit_output/*.json
```

## 7. 清理本地源码 `scripts/clean_source.sh`

```bash
bash scripts/clean_source.sh
```

会二次确认后清空 `source_code/*`，保留 `audit_output/`。

## 8. 自定义规则

1. 在 `rules/<语言>/` 下新建 yaml（参考现有文件格式）：

```yaml
rules:
  - id: php-include-userinput
    pattern: include $_GET[...];
    message: 用户输入直接进入 include，可能存在文件包含
    languages: [php]
    severity: ERROR
```

2. 在 `semgrep_batch_scan.sh` 顶部把对应变量指向新文件，或直接改成扫描整个 `rules/` 目录：

```bash
semgrep scan --config rules --json "${project}" > "${OUTPUT_DIR}/${project_name}_report.json"
```

> 元变量以大写字母开头（如 `$ARG`、`$OBJ`）；小写形式（如 `$db`）在 PHP 中会被当作字面变量名，不会匹配任意变量。这是编写规则时最常见的失效原因。

### 关于污点模式

`php-sqli-taint`、`php-lfi-taint` 使用 semgrep 的 `mode: taint`，只报告「用户输入确实流到危险函数」的路径，因此不会把 `include 'header.php'`、`$db->query($sql)`（`$sql` 为常量）这类正常写法算作命中。相比纯 `pattern` 匹配，噪声低一个数量级，但也可能漏掉经过自定义过滤函数的间接流入——需要时可在 `pattern-sources` 里补充来源函数。

## 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 克隆超时 / Connection reset | 直连 GitHub 被限速 | 使用 `ghproxy` 等镜像前缀；或配置代理 |
| `semgrep not found` | 未安装 / 不在 PATH | `python3 -m pip install -r requirements.txt` 后重试 |
| `source_code not found` | 未先克隆 | 先执行 `batch_clone.py` |
| 项目被跳过，无报告 | 未识别到 php / java 文件 | 确认目录结构，或按需扩展语言判定 |
| `summary_report.py` 提示无报告 | `audit_output/` 为空 | 先执行 `semgrep_batch_scan.sh` |
| semgrep 卡住不动 | 版本检查 / 指标上报走了外网 | 脚本已内置 `--metrics off --disable-version-check`；仍卡住请检查代理设置 |
| `import utils` 报错 | 直接 `python batch_clone.py` 且未把 scripts 加入路径 | 用 `python3 scripts/batch_clone.py` 运行 |
| 规则命中为 0 | 元变量写成了小写，或规则语法不匹配 | 用 `semgrep --validate --config rules/php/basic-php-vuln.yaml` 校验 |

## 免责声明

本工具仅用于授权范围内的安全学习，请遵守 [DISCLAIMER.md](../DISCLAIMER.md)。

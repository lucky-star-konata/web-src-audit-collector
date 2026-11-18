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

> 当前版本 v1.1.0，可用 `python3 scripts/batch_clone.py --version` 或 `bash scripts/semgrep_batch_scan.sh --version` 查看。
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
python3 scripts/batch_clone.py --depth 1          # 浅克隆，只取最新提交
python3 scripts/batch_clone.py --retry 2 --timeout 600
python3 scripts/batch_clone.py --repo-list other.txt
```

行为说明：

- 读取清单，逐行克隆到 `source_code/<仓库名>/`
- 目标目录已存在则打印 `[SKIP]` 跳过，不会重复下载
- 单仓库克隆超时默认 300 秒，可用 `--timeout` 调整
- 失败清理残留目录并自动重试（默认 1 次），重试仍失败则打印 `[FAIL]` 并计入汇总
- `--depth 1` 开启浅克隆，适合只做静态扫描、不需要历史记录的场景
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
bash scripts/semgrep_batch_scan.sh --keep-stale   # 保留已删除项目的旧报告
bash scripts/semgrep_batch_scan.sh --version
```

行为说明：

1. 前置检查：`semgrep` 是否安装、`source_code/` 与 `rules/` 是否存在
2. 扫描前清理陈旧报告：`source_code/` 中已不存在的项目，其 `*_report.json` 会被删除
3. 遍历 `source_code/` 下每个项目（统计时已排除 `vendor/`、`node_modules/`、`.git/`）
4. 含 `.php` 文件 → 以 `rules/php/` 为规则集扫描；含 `.java` 文件 → 以 `rules/java/` 为规则集扫描；两种都有则各出一份报告
5. 两类都没有 → 跳过该项目
6. 报告先写入 `.tmp`，semgrep 退出码为 0 且输出包含 `results` 字段才转正；失败打印 `[FAIL]` 并删除临时文件
7. 结束时输出 `scanned / failed / skipped / pruned_stale` 统计；存在扫描失败时脚本退出码为 1

产物：

```
audit_output/
├── zentaopms_php_report.json
├── emlog_php_report.json
└── JeecgBoot_java_report.json
```

> 规则新增方式：把 yaml 放进对应 `rules/<语言>/` 目录即可，脚本直接以目录为 `--config`，不需要改脚本。

## 5. 生成汇总 `scripts/summary_report.py`

```bash
python3 scripts/summary_report.py
```

读取 `audit_output/*_report.json`，输出 `audit_output/summary.md`，包含：

- 生成时间与项目/命中总数
- 项目概览表（项目、语言、各等级命中数）
- 规则命中排行（Top 20）
- 每个项目的命中明细（项目内相对路径:行号 + 规则 ID + 说明，单项目最多展示 200 条）

路径会统一为正斜杠并裁剪到项目根目录，Windows 与 Linux 产出的报告可以混读。单个报告 JSON 损坏时会打印 `[WARN]` 并跳过，不影响其余报告。

## 6. 收敛与 Triage `scripts/triage_report.py`

`summary_report.py` 负责"把所有命中原样列出来"，`triage_report.py` 负责"把告警收敛成可人工判定的清单"：

```bash
# 基础用法：排除 vendor/target/tests 等目录，去重后输出 triage.md / triage.json
python3 scripts/triage_report.py

# 只输出相对基线新增的命中（修复回归时使用）
python3 scripts/triage_report.py --baseline audit_output/baseline

# 叠加白名单，并限制清单长度
python3 scripts/triage_report.py --whitelist triage_whitelist.txt --top 500
```

处理流程：读取 `*_report.json` → 排除第三方/测试目录 → 按「项目 + 规则 + 文件 + 行号」去重 → 白名单过滤 → 基线对比 → 按严重级排序输出。

产物：

- `audit_output/triage.md`：统计概览 + 项目 × 规则分布 + 待判定清单（含「入口对外 / 参数可控 / 有效过滤」三列，供人工填写）
- `audit_output/triage.json`：结构化结果，便于脚本二次处理

白名单格式（`#` 开头为注释，规则 ID 支持 `*`）：

```
# 规则ID|路径子串
php-file-upload|install/
php-danger-eval|tests/
*|third_party/legacy/
```

> 默认排除目录为 `vendor/ node_modules/ target/ tests/ test/ third_party/ static/lib/`。若这些词恰好出现在业务路径中，用 `--no-default-exclude` 关闭默认排除，再用 `--extra-exclude` 精确指定。

## 7. 解读报告

报告是标准 Semgrep JSON，关键字段在 `results[]`：`check_id`（规则 ID）、`path`、`start.line`、`extra.message`、`extra.severity`。

```bash
# 每个规则的命中数量
jq -r '.results[] | .check_id' audit_output/*.json | sort | uniq -c | sort -rn

# 列出所有命中的文件与行号
jq -r '.results[] | "\(.path):\(.start.line) [\(.check_id)]"' audit_output/*.json
```

## 8. 清理本地源码 `scripts/clean_source.sh`

```bash
bash scripts/clean_source.sh
```

会二次确认后清空 `source_code/*`，保留 `audit_output/`。

## 9. 自定义规则

1. 在 `rules/<语言>/` 下新建 yaml（参考现有文件格式）：

```yaml
rules:
  - id: php-include-userinput
    pattern: include $_GET[...];
    message: 用户输入直接进入 include，可能存在文件包含
    languages: [php]
    severity: ERROR
```

2. 扫描脚本按语言目录加载规则，放进 `rules/<语言>/` 即生效，无需修改脚本：

```bash
semgrep scan --config rules/php --json "${project}" > "${OUTPUT_DIR}/${project_name}_php_report.json"
```

> 元变量以大写字母开头（如 `$ARG`、`$OBJ`）；小写形式（如 `$db`）在 PHP 中会被当作字面变量名，不会匹配任意变量。这是编写规则时最常见的失效原因。

### 关于污点模式

`php-sqli-taint`、`php-lfi-taint` 使用 semgrep 的 `mode: taint`，只报告「用户输入确实流到危险函数」的路径，因此不会把 `include 'header.php'`、`$db->query($sql)`（`$sql` 为常量）这类正常写法算作命中。相比纯 `pattern` 匹配，噪声低一个数量级，但也可能漏掉经过自定义过滤函数的间接流入——需要时可在 `pattern-sources` 里补充来源函数。

## 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 克隆超时 / Connection reset | 直连 GitHub 被限速 | 使用 `ghproxy` 等镜像前缀；或配置代理 |
| 克隆偶发失败 | 网络抖动 | 默认已重试 1 次，可用 `--retry N` 调整 |
| 扫描结束退出码为 1 | 有项目 semgrep 报错或输出非 JSON | 查看 `[FAIL]` 行与 `*_report.json.tmp` 删除原因，修复后重跑 |
| 旧项目报告仍出现在汇总里 | 默认会自动清理，但可能加了 `--keep-stale` | 去掉该参数重跑，或手动删除 `audit_output/*_report.json` |
| `semgrep not found` | 未安装 / 不在 PATH | `python3 -m pip install -r requirements.txt` 后重试 |
| `source_code not found` | 未先克隆 | 先执行 `batch_clone.py` |
| 项目被跳过，无报告 | 未识别到 php / java 文件 | 确认目录结构，或按需扩展语言判定 |
| `summary_report.py` 提示无报告 | `audit_output/` 为空 | 先执行 `semgrep_batch_scan.sh` |
| semgrep 卡住不动 | 版本检查 / 指标上报走了外网 | 脚本已内置 `--metrics off --disable-version-check`；仍卡住请检查代理设置 |
| `import utils` 报错 | 直接 `python batch_clone.py` 且未把 scripts 加入路径 | 用 `python3 scripts/batch_clone.py` 运行 |
| 规则命中为 0 | 元变量写成了小写，或规则语法不匹配 | 用 `semgrep --validate --config rules/php/basic-php-vuln.yaml` 校验 |

## 免责声明

本工具仅用于授权范围内的安全学习，请遵守 [DISCLAIMER.md](../DISCLAIMER.md)。

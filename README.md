# web-src-audit-collector

批量拉取开源 Web 项目源码，并用 Semgrep 规则做静态扫描，用于代码审计学习与漏洞模式积累。

> 仅用于**授权范围内**的代码审计学习。详见 [DISCLAIMER.md](./DISCLAIMER.md)。

## 特性

- **批量克隆**：从 `repo_list.txt` 逐行读取仓库地址，自动跳过已存在目录，单仓库克隆超时保护，失败残留自动清理
- **按语言分流扫描**：统计项目内 `.php` / `.java` 文件数量，自动选择对应规则集，避免规则错配
- **输出 JSON 报告**：每个项目独立生成 `*_php_report.json` / `*_java_report.json`，便于二次聚合
- **一键汇总**：`summary_report.py` 把 JSON 聚合为 Markdown（项目概览 + 规则排行 + 命中明细）
- **规则可扩展**：`rules/` 下按语言分目录，新增 yaml 即生效
- **路径无关**：所有脚本以仓库根目录为基准，在任意工作目录执行行为一致
- **镜像源支持**：`repo_list.txt` 默认带 `ghproxy` 镜像前缀，规避直连 GitHub 超时

## 目录结构

```
web-src-audit-collector/
├── repo_list.txt                  # 待审计仓库清单，一行一个 git 地址
├── scripts/
│   ├── batch_clone.py             # 批量克隆入口
│   ├── utils.py                   # 公共路径 / 仓库名解析
│   ├── semgrep_batch_scan.sh      # 批量扫描入口
│   ├── summary_report.py          # 报告汇总（JSON -> Markdown）
│   └── clean_source.sh            # 清理本地源码
├── rules/
│   ├── php/basic-php-vuln.yaml    # PHP 基础危险函数规则
│   └── java/basic-java-vuln.yaml  # Java 基础注入规则
├── docs/usage.md                  # 详细使用说明
├── source_code/                   # 克隆结果（gitignore，不入库）
└── audit_output/                  # 扫描报告与汇总（gitignore，不入库）
```

## 环境要求

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.8+ | 运行 `batch_clone.py` |
| Git | 任意较新版本 | 克隆源码 |
| Semgrep | 最新版 | 静态扫描 |
| Bash | —— | 运行 `.sh` 脚本（Windows 用 WSL / Git Bash） |

## 快速开始

```bash
git clone https://github.com/lucky-star-konata/web-src-audit-collector.git
cd web-src-audit-collector
python3 -m pip install semgrep
```

1. 编辑 `repo_list.txt`，每行一个仓库地址，`#` 开头为注释：

```
https://github.com/easysoft/zentaopms.git
https://github.com/emlog/emlog.git
```

2. 批量克隆：

```bash
python3 scripts/batch_clone.py
```

3. 批量扫描：

```bash
bash scripts/semgrep_batch_scan.sh
```

4. 生成汇总报告：

```bash
python3 scripts/summary_report.py
```

5. 查看 `audit_output/` 下的 JSON 报告与 `summary.md`。清理源码：

```bash
bash scripts/clean_source.sh
```

## 规则说明

`rules/php/basic-php-vuln.yaml`

| 规则 ID | 匹配内容 | 等级 |
| --- | --- | --- |
| `php-sql-query-variable` | `query()` / `exec()` / `mysqli_query()` 参数为变量 | WARNING |
| `php-danger-eval` | `eval(...)` | ERROR |
| `php-danger-command-exec` | `system` / `exec` / `shell_exec` / `passthru` / `popen` / `proc_open` | ERROR |
| `php-danger-unserialize` | `unserialize(...)` | ERROR |
| `php-file-include` | `include` / `require` 参数为变量 | WARNING |
| `php-file-upload` | `move_uploaded_file(...)` 文件落盘点 | WARNING |

`rules/java/basic-java-vuln.yaml`

| 规则 ID | 匹配内容 | 等级 |
| --- | --- | --- |
| `java-sql-statement-concat` | `executeQuery` / `executeUpdate` / `execute` 字符串拼接 | WARNING |
| `java-runtime-exec` | `Runtime.getRuntime().exec(...)` | ERROR |
| `java-process-builder` | `new ProcessBuilder(...)` | WARNING |
| `java-deserialization` | `new ObjectInputStream(...)` | WARNING |

新增规则：在 `rules/<语言>/` 下新建 `*.yaml`，然后把它加入 `semgrep_batch_scan.sh` 顶部对应变量（或直接改成扫描 `rules/` 整个目录）。

## 输出说明

```
audit_output/
├── zentaopms_php_report.json
├── emlog_php_report.json
├── JeecgBoot_java_report.json
└── summary.md              # 汇总报告（项目概览 + 规则排行 + 命中明细）
```

报告为标准 Semgrep JSON，也可用 `jq` 快速提取：

```bash
# 统计每个项目的命中数量
jq -r '.results[] | .check_id' audit_output/*.json | sort | uniq -c | sort -rn
```

## 常见问题

**Q：克隆超时 / 连接被重置？**
`repo_list.txt` 已使用 `https://mirror.ghproxy.com/` 前缀镜像。若镜像失效，可替换为其他可用镜像，或本地配置代理后直连。

**Q：Semgrep 未安装提示？**
`pip install semgrep` 后确认 `semgrep --version` 可执行；conda 环境需先激活。

**Q：Semgrep 卡住无响应？**
扫描脚本已内置 `--metrics off --disable-version-check --no-rewrite-rule-ids`，避免版本检查与指标上报走外网。若仍卡住，检查系统代理设置（代理不可达时 semgrep 会长时间等待）。

**Q：项目既含 PHP 又含 Java？**
脚本优先按 PHP 判定（`if` 在前）。如需两者都扫，把该段改成两个独立的 `if` 分支。

**Q：Windows 下脚本跑不起来？**
`.sh` 脚本需要 Bash，建议使用 WSL 或 Git Bash，并在仓库根目录执行。

## License

[MIT](./LICENSE)

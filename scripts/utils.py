from pathlib import Path
import re

def init_dir():
    Path("./source_code").mkdir(exist_ok=True)
    Path("./scan_result").mkdir(exist_ok=True)

def get_repo_name(git_url: str):
    # 从git链接提取仓库名称
    res = re.search(r"/([^/]+)\.git$", git_url)
    if res:
        return res.group(1)
    res2 = re.search(r"/([^/]+)$", git_url)
    if res2:
        return res2.group(1)
    return "unknown_repo"

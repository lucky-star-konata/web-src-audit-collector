from pathlib import Path

# 以仓库根目录为基准，保证在任意工作目录下运行脚本行为一致
ROOT = Path(__file__).resolve().parent.parent
SAVE_ROOT = ROOT / "source_code"
OUTPUT_ROOT = ROOT / "audit_output"
REPO_LIST = ROOT / "repo_list.txt"

def init_dir():
    """Create local folder for source and report"""
    SAVE_ROOT.mkdir(exist_ok=True)
    OUTPUT_ROOT.mkdir(exist_ok=True)

def get_repo_name(git_url: str) -> str:
    """Extract repo name from git url (handles trailing slash and .git suffix)"""
    name = git_url.strip().rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name

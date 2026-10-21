from pathlib import Path

SAVE_ROOT = Path("./source_code")
OUTPUT_ROOT = Path("./audit_output")

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

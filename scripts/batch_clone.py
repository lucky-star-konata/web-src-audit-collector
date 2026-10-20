import subprocess
from pathlib import Path
from utils import init_dir, get_repo_name

REPO_LIST = "repo_list.txt"
SAVE_ROOT = Path("./source_code")

def clone_single(git_url: str):
    repo_name = get_repo_name(git_url)
    target = SAVE_ROOT / repo_name
    if target.exists():
        print(f"[SKIP] {repo_name} already exists.")
        return
    print(f"[CLONE] Pulling {git_url}")
    try:
        subprocess.run(
            ["git", "clone", git_url, str(target)],
            timeout=300,
            capture_output=False
        )
    except Exception as e:
        print(f"[FAIL] Clone {git_url} error: {e}")

def main():
    init_dir()
    with open(REPO_LIST, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        clone_single(line)
    print("\n[FINISH] All clone tasks done.")

if __name__ == "__main__":
    main()

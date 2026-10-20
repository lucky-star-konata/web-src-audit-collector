import subprocess
from pathlib import Path
from utils import init_dir, get_repo_name

REPO_LIST = "repo_list.txt"
SAVE_ROOT = Path("./source_code")

def clone_repo(git_url):
    repo_name = get_repo_name(git_url)
    target_path = SAVE_ROOT / repo_name
    if target_path.exists():
        print(f"[SKIP] {repo_name} already exists.")
        return
    print(f"[CLONE] Pulling {git_url} ...")
    try:
        subprocess.run(
            ["git", "clone", git_url, str(target_path)],
            timeout=300,
            check=True
        )
        print(f"[OK] {repo_name} download complete")
    except Exception as e:
        print(f"[FAIL] Clone error: {e}")

if __name__ == "__main__":
    init_dir()
    with open(REPO_LIST, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        clone_repo(line)
    print("\n==== All clone tasks finished ====")

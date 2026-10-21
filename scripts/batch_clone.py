import subprocess
import shutil
from pathlib import Path
from utils import init_dir, get_repo_name

REPO_LIST = "repo_list.txt"
SAVE_ROOT = Path("./source_code")

def clone_single(git_url: str) -> str:
    """Clone one repo. Returns one of: created / skipped / failed."""
    repo_name = get_repo_name(git_url)
    target = SAVE_ROOT / repo_name
    if target.exists():
        print(f"[SKIP] {repo_name} already exists.")
        return "skipped"
    print(f"[CLONE] Pulling {git_url}")
    try:
        result = subprocess.run(
            ["git", "clone", git_url, str(target)],
            timeout=300,
            capture_output=False
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, "git clone")
    except Exception as e:
        # 失败时清理残留目录，避免下次被误判为已存在而永久 SKIP
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        print(f"[FAIL] Clone {git_url} error: {e}")
        return "failed"
    print(f"[OK] {repo_name} -> {target}")
    return "created"

def main():
    init_dir()
    with open(REPO_LIST, "r", encoding="utf-8") as f:
        lines = f.readlines()
    stats = {"created": 0, "skipped": 0, "failed": 0}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        stats[clone_single(line)] += 1
    print(
        f"\n[FINISH] All clone tasks done. "
        f"success={stats['created']} skipped={stats['skipped']} failed={stats['failed']}"
    )

if __name__ == "__main__":
    main()

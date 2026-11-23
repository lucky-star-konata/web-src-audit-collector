import argparse
import shutil
import subprocess
import time
from pathlib import Path

from utils import (
    REPO_LIST, SAVE_ROOT, VERSION, get_repo_name, init_dir, validate_git_url,
)


def clone_single(git_url: str, retries: int = 1, depth: int = 0, timeout: int = 300) -> str:
    """Clone one repo. Returns one of: created / skipped / failed."""
    try:
        git_url = validate_git_url(git_url)
        repo_name = get_repo_name(git_url)
    except ValueError as e:
        print(f"[FAIL] {e}")
        return "failed"

    save_root = SAVE_ROOT.resolve()
    target = (save_root / repo_name).resolve()
    if target.parent != save_root:
        print(f"[FAIL] 仓库名解析后越界，已拒绝: {repo_name}")
        return "failed"
    if target.exists():
        print(f"[SKIP] {repo_name} already exists.")
        return "skipped"

    cmd = ["git", "clone"]
    if depth > 0:
        cmd += ["--depth", str(depth)]
    cmd += ["--", git_url, str(target)]

    attempt = 0
    while True:
        attempt += 1
        print(f"[CLONE] Pulling {git_url} (attempt {attempt})")
        try:
            result = subprocess.run(cmd, timeout=timeout)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "git clone")
        except Exception as e:
            # 失败时清理残留目录，避免下次被误判为已存在而永久 SKIP
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            if attempt <= retries:
                print(f"[RETRY] Clone failed ({e}), retrying in 2s ...")
                time.sleep(2)
                continue
            print(f"[FAIL] Clone {git_url} error: {e}")
            return "failed"
        print(f"[OK] {repo_name} -> {target}")
        return "created"


def main():
    parser = argparse.ArgumentParser(description="批量克隆 repo_list.txt 中的仓库")
    parser.add_argument("--repo-list", default=str(REPO_LIST), help="仓库清单路径，默认 repo_list.txt")
    parser.add_argument("--retry", type=int, default=1, help="单个仓库失败后的重试次数，默认 1")
    parser.add_argument("--depth", type=int, default=0, help="浅克隆深度，0 表示完整克隆（默认）")
    parser.add_argument("--timeout", type=int, default=300, help="单仓库克隆超时秒数，默认 300")
    parser.add_argument("--dry-run", action="store_true", help="只校验地址并打印克隆计划，不执行克隆")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    init_dir()
    repo_list = Path(args.repo_list)
    if not repo_list.exists():
        raise SystemExit(f"[!] {repo_list} not found")

    with open(repo_list, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    stats = {"created": 0, "skipped": 0, "failed": 0}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if args.dry_run:
            try:
                url = validate_git_url(line)
                target = SAVE_ROOT / get_repo_name(url)
                print(f"[DRY-RUN] {url} -> {target}")
            except ValueError as e:
                print(f"[FAIL] {e}")
                stats["failed"] += 1
            continue
        stats[clone_single(line, retries=args.retry, depth=args.depth, timeout=args.timeout)] += 1

    print(
        f"\n[FINISH] All clone tasks done. "
        f"success={stats['created']} skipped={stats['skipped']} failed={stats['failed']}"
    )


if __name__ == "__main__":
    main()

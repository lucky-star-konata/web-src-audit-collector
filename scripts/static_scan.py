import subprocess
from pathlib import Path
from utils import init_dir

SRC_ROOT = Path("./source_code")
OUTPUT_ROOT = Path("./scan_result")

def run_semgrep_scan(target_dir, repo_name):
    out_file = OUTPUT_ROOT / f"{repo_name}_semgrep.json"
    print(f"[SCAN] Start static scan for {repo_name}")
    cmd = [
        "semgrep", "scan",
        "--config=p/php",
        "--json",
        "-o", str(out_file),
        str(target_dir)
    ]
    try:
        subprocess.run(cmd, timeout=600)
        print(f"[DONE] Report saved: {out_file}")
    except Exception as e:
        print(f"[ERROR] Scan failed: {e}")

if __name__ == "__main__":
    init_dir()
    for repo_dir in SRC_ROOT.iterdir():
        if repo_dir.is_dir():
            run_semgrep_scan(repo_dir, repo_dir.name)
    print("\n==== All static scan tasks finished ====")

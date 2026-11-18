from pathlib import Path

# 以仓库根目录为基准，保证在任意工作目录下运行脚本行为一致
ROOT = Path(__file__).resolve().parent.parent
SAVE_ROOT = ROOT / "source_code"
OUTPUT_ROOT = ROOT / "audit_output"
REPO_LIST = ROOT / "repo_list.txt"
VERSION_FILE = ROOT / "VERSION"


def get_version() -> str:
    """读取仓库根目录 VERSION 文件，缺失时回退为 0.0.0"""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = get_version()


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


def normalize_path(raw_path: str) -> str:
    """统一分隔符，兼容 Windows 反斜杠路径"""
    return (raw_path or "").replace("\\", "/")


def project_relative(raw_path: str, project: str) -> str:
    """把绝对路径裁剪为项目内相对路径，便于基线与跨机器对比"""
    path = normalize_path(raw_path)
    marker = f"/{project}/"
    if marker in path:
        return path.split(marker, 1)[1]
    return path

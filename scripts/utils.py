import re
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


SCP_LIKE_RE = re.compile(r"^[\w.-]+@[\w.-]+:")
ALLOWED_SCHEMES = ("http://", "https://", "ssh://", "git://")


def validate_git_url(git_url: str) -> str:
    """只允许常见传输协议，挡住 ext:: 远程助手与参数注入。

    git 的 ext:: 传输会执行任意命令，repo_list.txt 一旦被替换即可 RCE；
    以 '-' 开头的地址还会被 git 当成命令行选项。
    """
    url = git_url.strip()
    if not url or any(ch in url for ch in ("\x00", "\n", "\r")):
        raise ValueError("仓库地址为空或包含非法字符")
    if url.startswith("-"):
        raise ValueError(f"仓库地址不能以 '-' 开头: {url}")
    if SCP_LIKE_RE.match(url):
        return url
    if url.lower().startswith(ALLOWED_SCHEMES):
        return url
    raise ValueError(f"不支持的仓库地址，仅允许 http/https/ssh/git 或 git@host:path: {url}")


def get_repo_name(git_url: str) -> str:
    """Extract repo name from git url (handles trailing slash and .git suffix)"""
    name = git_url.strip().rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    if not name or name in (".", "..") or any(ch in name for ch in ("/", "\\", "\x00")):
        raise ValueError(f"无法从地址中安全解析仓库名: {git_url}")
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

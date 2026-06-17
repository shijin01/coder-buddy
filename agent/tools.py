import pathlib
import subprocess
from typing import Tuple

try:
    from langchain_core.tools import tool
except ImportError:
    try:
        from langchain.tools import tool
    except ImportError as exc:
        raise ImportError(
            "Missing langchain tools dependency. Install langchain-core or langchain."
        ) from exc

PROJECT_ROOT = pathlib.Path.cwd() / "generated_project"


def safe_path_for_project(path: str, job_id: str) -> pathlib.Path:
    job_root = (PROJECT_ROOT / job_id).resolve()
    filepath = "/".join(path.split("/")[0:-1])
    if(filepath=="/"):
        filepath = job_root.absolute()/path
    else:
        filepath = job_root.absolute()/filepath/path.split("/")[-1]
    p = (filepath).resolve()
    if job_root not in p.parents and job_root != p:
        print(job_root.absolute(),p.absolute(),path,sep=",\t")
        raise ValueError("Attempt to write outside project root")
    return p


@tool
def write_file(path: str, job_id:str,content: str) -> str:
    """Writes content to a file at the specified path within the project root.The actual path of the file should be under the job_id in project directory."""
    p = safe_path_for_project(path,job_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return f"WROTE:{p}"


@tool
def read_file(path: str, job_id:str) -> str:
    """Reads content from a file at the specified path within the project root.The actual path of the file should be under the job_id in project directory."""
    p = safe_path_for_project(path,job_id)
    if not p.exists():
        return ""
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


@tool
def get_current_directory(job_id: str) -> str:
    """Returns the current working directory for the specified job."""
    return str((PROJECT_ROOT / job_id).resolve())


@tool
def list_files(job_id: str, directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root.The valid directory should be under the job_id in project directory."""
    p = safe_path_for_project(directory, job_id)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(PROJECT_ROOT / job_id)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."

@tool
def run_cmd(cmd: str, job_id: str, cwd: str = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result.The valid directory should be under the job_id in project directory."""
    cwd_dir = safe_path_for_project(cwd or ".", job_id)
    res = subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return res.returncode, res.stdout, res.stderr


def init_project_root(job_id: str) -> str:
    job_root = (PROJECT_ROOT / job_id).resolve()
    job_root.mkdir(parents=True, exist_ok=True)
    return str(job_root)

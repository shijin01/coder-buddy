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


import pathlib

# Assuming PROJECT_ROOT is defined elsewhere, e.g.:
# PROJECT_ROOT = pathlib.Path("D:/projects")

def safe_path_for_project(path: str, job_id: str) -> pathlib.Path:
    job_root = (PROJECT_ROOT / job_id).resolve()
    path_obj = pathlib.Path(path)

    # 1. Strip ANY root or drive anchor (e.g., '/', '\', or 'C:\')
    # This safely forces the path to be relative, fixing the Windows leading-slash issue.
    if path_obj.anchor:
        path_obj = path_obj.relative_to(path_obj.anchor)

    # 2. Prevent redundant job_id nesting (e.g., if path is "job_123/public/index.html")
    if path_obj.parts and path_obj.parts[0] == job_id:
        path_obj = pathlib.Path(*path_obj.parts[1:])

    # 3. Join the cleaned path to the root and RESOLVE it. 
    final_path = (job_root / path_obj).resolve()

    # 4. Verify the final path is strictly inside the job_root
    try:
        final_path.relative_to(job_root)
    except ValueError:
        print(f"{job_root.absolute()},\t{final_path.absolute()},\t{path}")
        raise ValueError(
            f"Attempt to write outside project root. "
            f"Expected: {path} ---- Created: {final_path.absolute()}"
        )

    return final_path


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

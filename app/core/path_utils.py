from pathlib import Path
import os

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))).resolve()

APP_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))).resolve()

def get_project_path(relative_path: str = "") -> Path:
    return PROJECT_ROOT.joinpath(relative_path).resolve()

def get_app_path(relative_path: str = "") -> Path:
    return APP_ROOT.joinpath(relative_path).resolve()

def ensure_path_exists(path: Path, create_dir: bool = False) -> Path:
    if not path.exists() and create_dir and not path.is_file():
        path.mkdir(parents=True, exist_ok=True)
    elif not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return path

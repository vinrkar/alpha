# src/utils/tree.py

from pathlib import Path

IGNORED_ENTRIES: set[str] = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "rubric_ai.egg-info",
    ".idea",
    "chroma_db",
}

def show_tree(dir_path: Path, prefix: str = "") -> None:
    """Prints a filtered directory tree for the project."""
    entries = sorted(
        path
        for path in dir_path.iterdir()
        if path.name not in IGNORED_ENTRIES
        and not (path.is_file() and path.name == "__init__.py")
    )
    pointers = ["├── "] * (len(entries) - 1) + ["└── "] if entries else []

    for pointer, path in zip(pointers, entries):
        print(f"{prefix}{pointer}{path.name}")
        if path.is_dir():
            extension = "│   " if pointer == "├── " else "    "
            show_tree(path, prefix + extension)

if __name__ == "__main__":
    root_dir = Path(".")
    print(f"📁 {root_dir.resolve().name}/")
    show_tree(root_dir)
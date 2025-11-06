#!/usr/bin/env python3
"""
Create a task folder structure under:
\\spatialfiles2\work\FOR\RSI\SA\Tasks\<year>\<task_id>\{Deliverables, Incoming, Working}

- If a folder already exists, it will NOT be deleted — only a warning shown.
- Works on Windows (network drive UNC path).
"""

from pathlib import Path
import sys

BASE_DIR = Path(r"\\spatialfiles2\work\FOR\RSI\SA\Tasks")
YEAR = "2025"
SUBDIRS = ("Deliverables", "Incoming", "Working")

def create_task_structure(task_id: str) -> Path:
    """Create the folder structure for a given task ID."""
    if not task_id or str(task_id).strip() == "":
        raise ValueError("Invalid input. Please provide a non-empty task_id.")

    # Define paths
    year_dir = BASE_DIR / YEAR
    task_dir = year_dir / task_id

    # Ensure year directory exists
    try:
        year_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Failed to create or access year directory: {year_dir}\n{e}", file=sys.stderr)
        raise

    # Create the main task directory
    if task_dir.exists():
        print(f"⚠️  WARNING: Task folder already exists and will not be modified: {task_dir}")
    else:
        try:
            task_dir.mkdir(parents=False, exist_ok=False)
            print(f"✅ Created task folder: {task_dir}")
        except Exception as e:
            print(f"ERROR: Failed to create task folder: {task_dir}\n{e}", file=sys.stderr)
            raise

    # Create subdirectories
    for name in SUBDIRS:
        sub = task_dir / name
        if sub.exists():
            print(f"⚠️  Subdirectory already exists: {sub}")
        else:
            try:
                sub.mkdir()
                print(f"✅ Created subdirectory: {sub}")
            except Exception as e:
                print(f"ERROR: Failed to create subdirectory: {sub}\n{e}", file=sys.stderr)
                raise

    return task_dir


# Example: Automatically create folder for task 928 when script runs
if __name__ == "__main__":
    create_task_structure("1160")    # <------------------

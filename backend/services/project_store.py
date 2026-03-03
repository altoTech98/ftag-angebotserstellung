"""
Project Store – Manages project metadata for folder uploads.

Each project groups multiple uploaded files together with their
classification and analysis state. Stored in data/projects.json.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
MAX_PROJECTS = 20


def _load_projects() -> list[dict]:
    """Load all projects from JSON file."""
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.warning("Could not load projects file, starting fresh")
        return []


def _save_projects(projects: list[dict]):
    """Save all projects to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def create_project(files: list[dict], project_id: str = None) -> dict:
    """
    Create a new project entry.

    Args:
        files: [{"file_id": str, "filename": str, "category": str,
                 "confidence": float, "reason": str, "parseable": bool, "size": int}]
        project_id: Optional pre-generated project ID.

    Returns:
        Full project dict with project_id, created_at, status.
    """
    if not project_id:
        project_id = str(uuid.uuid4())[:12]

    # Strip file_path from entries (no longer stored on disk)
    clean_files = []
    for f in files:
        clean = {k: v for k, v in f.items() if k != "file_path"}
        clean_files.append(clean)

    project = {
        "project_id": project_id,
        "files": clean_files,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "classified",  # classified → analyzing → analyzed → error
        "total_files": len(clean_files),
        "summary": _compute_summary(clean_files),
    }

    projects = _load_projects()
    projects.insert(0, project)

    # Enforce maximum projects
    if len(projects) > MAX_PROJECTS:
        projects = projects[:MAX_PROJECTS]

    _save_projects(projects)

    return project


def get_project(project_id: str) -> dict | None:
    """Retrieve a project by ID."""
    projects = _load_projects()
    for p in projects:
        if p["project_id"] == project_id:
            return p
    return None


def update_project(project_id: str, updates: dict) -> dict | None:
    """
    Update project fields.

    Args:
        project_id: Project to update
        updates: Dict of fields to merge into project

    Returns:
        Updated project or None if not found.
    """
    projects = _load_projects()
    for p in projects:
        if p["project_id"] == project_id:
            p.update(updates)
            _save_projects(projects)
            return p
    return None


def update_file_classification(
    project_id: str, file_id: str, new_category: str
) -> dict | None:
    """
    User manually reclassifies a file within a project.

    Returns:
        Updated project or None if not found.
    """
    valid_categories = {"tuerliste", "spezifikation", "plan", "foto", "sonstig"}
    if new_category not in valid_categories:
        raise ValueError(f"Invalid category: {new_category}. Must be one of {valid_categories}")

    projects = _load_projects()
    for p in projects:
        if p["project_id"] == project_id:
            for f in p["files"]:
                if f["file_id"] == file_id:
                    f["category"] = new_category
                    f["confidence"] = 1.0
                    f["reason"] = "Manuell klassifiziert"
                    f["parseable"] = new_category in ("tuerliste", "spezifikation")
                    break
            p["summary"] = _compute_summary(p["files"])
            _save_projects(projects)
            return p
    return None


def _compute_summary(files: list[dict]) -> dict:
    """Compute category counts."""
    summary = {
        "tuerliste_count": 0,
        "spezifikation_count": 0,
        "plan_count": 0,
        "foto_count": 0,
        "sonstig_count": 0,
    }
    for f in files:
        key = f"{f.get('category', 'sonstig')}_count"
        if key in summary:
            summary[key] += 1
    return summary

"""Shared helpers for the job-scout skill tests: load its scripts by path, build test files."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from repo_model import REPO_ROOT

SKILL = REPO_ROOT / "plugins" / "emad-jobs" / "skills" / "job-scout"
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"


def load(name: str):
    """Import one of the skill's scripts as a module, the way the scripts import each other."""
    if name in sys.modules and getattr(sys.modules[name], "__file__", "").startswith(str(SCRIPTS)):
        return sys.modules[name]
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def job(**fields) -> dict:
    """A valid tracker entry. Pass fields to override the defaults."""
    entry = {
        "id": "acme-staff-engineer",
        "title": "Staff Engineer",
        "company": "Acme",
        "url": "https://jobs.ashbyhq.com/acme/3f9d85f6-0750-400f-a129-6a0f8ab76476",
        "status": "new",
        "score": 8,
        "location": "Remote - Europe",
        "work_style": "remote",
        "compensation": "Not listed",
        "why": "Builds agent tooling.",
        "watch_out": "",
        "source": "ashby:acme",
        "published": "2026-11-01",
        "first_seen": "2026-11-02",
        "last_verified": "2026-11-02",
        "applied_date": None,
        "notes": "",
        "my_notes": "",
        "vendor": "Ashby",
        "channel": "portal",
        "human_contact": None,
        "hiring_manager": "",
        "resume": None,
        "history": [{"status": "new", "date": "2026-11-02", "by": "agent"}],
    }
    entry.update(fields)
    return entry


def write_jobs(folder: Path, jobs: list[dict]) -> Path:
    path = folder / "jobs.json"
    data = {
        "meta": {
            "version": 1,
            "statuses": ["new", "applied", "in_process", "rejected", "archived"],
        },
        "jobs": jobs,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def read_jobs(folder: Path) -> list[dict]:
    return json.loads((folder / "jobs.json").read_text(encoding="utf-8"))["jobs"]

#!/usr/bin/env python3
"""Shared file helpers for the job-scout scripts. Not a command: the other scripts import it.

Every script writes only inside the job search folder the user chose (--dir). Writes are
atomic (a temporary file, then a rename), and the tracker and the log are backed up before
the first write of each day.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

STATUSES = ("new", "applied", "in_process", "rejected", "archived")
# Files that get a dated copy in backups/ before they change.
BACKED_UP = ("jobs.json", "job-search.md", "search-config.json")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# How an application went in. The person decides; the agent records what they say.
CHANNELS = ("portal", "referral", "hiring-manager-direct", "recruiter-inbound", "community")

# Hiring software, found from the posting URL. Matching is by substring.
VENDOR_DOMAINS = (
    ("myworkdayjobs.com", "Workday"),
    ("greenhouse.io", "Greenhouse"),
    ("lever.co", "Lever"),
    ("ashbyhq.com", "Ashby"),
    ("icims.com", "iCIMS"),
    ("eightfold.ai", "Eightfold"),
    ("hirevue.com", "HireVue"),
    ("smartrecruiters.com", "SmartRecruiters"),
    ("recruitee.com", "Recruitee"),
    ("workable.com", "Workable"),
    ("personio.", "Personio"),
)


class FolderError(ValueError):
    """A path is outside the job search folder, or a required file is missing."""


def today_iso(value: str | None = None) -> str:
    if value is None:
        return date.today().isoformat()
    if not DATE_RE.match(value):
        raise FolderError(f"--today must look like 2026-11-10, got {value!r}")
    return value


def resolve_in(root: Path, path: str | Path) -> Path:
    """Resolve path against the folder and refuse anything that ends up outside it."""
    root = Path(root).resolve()
    candidate = Path(path)
    full = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if full != root and root not in full.parents:
        raise FolderError(f"{path} is outside the job search folder {root}; refusing to use it")
    return full


def write_text(path: Path, text: str) -> None:
    """Write a file atomically, so a crash never leaves half a file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FolderError(f"{path} does not exist") from None
    except json.JSONDecodeError as exc:
        raise FolderError(f"{path} is not valid JSON: {exc}") from None


def backup(root: Path, today: str, always: bool = False) -> list[Path]:
    """Copy the tracker, the log and the search config into backups/ with today's date.

    With always=False (used before each write) a file that already has a backup today is
    skipped, so the first backup of the day keeps the state before the run. With always=True
    (the `backup` command) a second backup gets a -2, -3 ... suffix. A backup is never
    overwritten or deleted.
    """
    root = Path(root)
    made = []
    for name in BACKED_UP:
        src = root / name
        if not src.is_file():
            continue
        stem, suffix = src.stem, src.suffix
        target = root / "backups" / f"{stem}.backup-{today}{suffix}"
        if target.exists():
            if not always:
                continue
            n = 2
            while target.exists():
                target = root / "backups" / f"{stem}.backup-{today}-{n}{suffix}"
                n += 1
        write_text(target, src.read_text(encoding="utf-8"))
        made.append(target)
    return made


def load_tracker(root: Path) -> dict:
    data = read_json(Path(root) / "jobs.json")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FolderError("jobs.json must be an object with a 'jobs' list")
    return data


def save_tracker(root: Path, data: dict, today: str) -> None:
    backup(root, today)
    data.setdefault("meta", {})["last_updated"] = today
    write_json(Path(root) / "jobs.json", data)


def detect_vendor(url: str | None) -> str:
    """Name the hiring software behind a posting URL."""
    u = (url or "").lower()
    for domain, name in VENDOR_DOMAINS:
        if domain in u:
            return name
    # A company careers page can still run on Greenhouse: gh_jid / gh_src are its ids.
    if re.search(r"[?&]gh_(jid|src)=", u):
        return "Greenhouse"
    return "company-own" if u else "unknown"


def derive_human_contact(job: dict):
    """Did a human ever take part in this application? True, False, or None (unknown).

    Reaching in_process always means yes. Otherwise an answer the person gave
    (human_contact_by == "user") is kept: a named recruiter may have written without the
    card moving. Otherwise a rejection with history means no, and anything else is unknown.
    """
    seen = [h.get("status") for h in job.get("history") or []]
    if "in_process" in seen:
        return True
    if job.get("human_contact_by") == "user":
        return job.get("human_contact")
    if job.get("status") == "rejected" and seen:
        return False
    return None

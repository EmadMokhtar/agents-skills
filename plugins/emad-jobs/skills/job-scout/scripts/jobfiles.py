#!/usr/bin/env python3
"""Shared file helpers for the job-scout scripts. Not a command: the other scripts import it.

Every script writes only inside the job search folder the user chose (--dir). Writes are
atomic (a temporary file, then a rename), and the tracker and the log are backed up before
the first write of each day.
"""

from __future__ import annotations

import errno
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

STATUSES = ("new", "applied", "in_process", "rejected", "archived")
# Files that get a dated copy in backups/ before they change.
BACKED_UP = ("jobs.json", "job-search.md", "search-config.json")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# How an application went in. The person decides; the agent records what they say.
CHANNELS = ("portal", "referral", "hiring-manager-direct", "recruiter-inbound", "community")

# Hiring software, found from the posting URL's host name: the host is the domain or ends
# in .<domain>. kanban.html has a copy of this list; a test keeps the two the same.
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
    ("personio.de", "Personio"),
    ("personio.com", "Personio"),
)


class FolderError(ValueError):
    """A path is outside the job search folder, a required file is missing, or a file in the
    folder cannot be read or written."""


def missing_folder(root: Path) -> str:
    return (
        f"the job search folder {root} does not exist here. If it is on the person's computer "
        "and this agent runs somewhere else (for example in a chat app's sandbox), use upload "
        "mode: see references/environments.md"
    )


def os_problem(exc: OSError, action: str = "use", path: Path | str | None = None) -> str:
    """Say in plain words why a file could not be read or written."""
    where = path or exc.filename or "a file in the job search folder"
    if exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
        return (
            f"cannot {action} {where}: permission denied. The folder is read-only, or this "
            f"agent is not allowed to {action} files there. Run check_folder.py --dir <folder> "
            "to see what works here (references/environments.md)"
        )
    return f"cannot {action} {where}: {exc.strerror or exc}"


def today_iso(value: str | None = None) -> str:
    if value is None:
        return date.today().isoformat()
    if not DATE_RE.match(value):
        raise FolderError(f"--today must look like 2026-11-10, got {value!r}")
    return value


def job_folder(value: str | Path) -> Path:
    """The job search folder from --dir, with a leading ~ expanded to the home folder.

    An agent often passes "~/job-search" in quotes, and then the shell does not expand it.
    """
    return Path(os.path.expanduser(str(value))).resolve()


def resolve_in(root: Path, path: str | Path) -> Path:
    """Resolve path against the folder and refuse anything that ends up outside it."""
    root = Path(root).resolve()
    candidate = Path(path)
    full = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if full != root and root not in full.parents:
        raise FolderError(f"{path} is outside the job search folder {root}; refusing to use it")
    return full


def write_text(path: Path, text: str) -> None:
    """Write a file atomically, so a crash never leaves half a file behind.

    A write the operating system refuses (a read-only folder, a full disk) raises FolderError
    with a plain message, so the scripts print it instead of a traceback.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    except OSError as exc:
        raise FolderError(os_problem(exc, "write", path)) from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError as exc:
        Path(tmp).unlink(missing_ok=True)
        raise FolderError(os_problem(exc, "write", path)) from None
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if not path.parent.is_dir():
            raise FolderError(missing_folder(path.parent)) from None
        raise FolderError(f"{path} does not exist") from None
    except OSError as exc:
        raise FolderError(os_problem(exc, "read", path)) from None
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
    if not root.is_dir():
        # Without this, a wrong --dir would back up nothing and still look like success.
        raise FolderError(missing_folder(root))
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
    root = Path(root)
    if root.is_dir() and not (root / "jobs.json").exists():
        raise FolderError(
            f"jobs.json does not exist in {root}. For a new job search, run "
            "check_folder.py --dir <folder> --init, then intake (references/intake.md)"
        )
    data = read_json(root / "jobs.json")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FolderError("jobs.json must be an object with a 'jobs' list")
    return data


def save_tracker(root: Path, data: dict, today: str) -> None:
    backup(root, today)
    data.setdefault("meta", {})["last_updated"] = today
    write_json(Path(root) / "jobs.json", data)


def _host(url: str) -> str:
    """The host name of a URL, also when it has no scheme ("jobs.lever.co/acme/1")."""
    try:
        return urlparse(url if "//" in url else "//" + url).hostname or ""
    except ValueError:
        return ""


def detect_vendor(url: str | None) -> str:
    """Name the hiring software behind a posting URL, from its host name."""
    u = (url or "").strip().lower()
    host = _host(u)
    for domain, name in VENDOR_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return name
    # A company careers page can still run on Greenhouse: gh_jid / gh_src are its ids.
    if re.search(r"[?&]gh_(jid|src)=", u):
        return "Greenhouse"
    return "company-own" if u else "unknown"


def derive_human_contact(job: dict):
    """Did a human ever take part in this application? True, False, or None (unknown).

    Reaching in_process always means yes. Otherwise an answer the person gave
    (human_contact_by == "user") is kept. Otherwise it is unknown, also after a rejection:
    a named recruiter may have written or called without the card ever moving, so only the
    person can say "no". The vendor report keeps a flag provisional until they do.
    """
    seen = [h.get("status") for h in job.get("history") or []]
    if "in_process" in seen:
        return True
    if job.get("human_contact_by") == "user":
        return job.get("human_contact")
    return None

#!/usr/bin/env python3
"""Check that this agent can use the job search folder, and set up a new one.

Run it before the first command of a session. It checks that the folder exists and can be
written to (it creates and deletes one small probe file), lists the job search files that
are there, and reports the tools the other scripts need. With --network it also checks
that the job board APIs answer from here. With --init it first creates a new folder from
the templates. It never overwrites a file, and never creates profile.yaml: intake writes it.

It cannot tell whether the folder stays after this conversation. A chat app's sandbox (a
temporary computer that the chat app runs code on) can be written to and is still removed
later. See references/environments.md.

Exit status: 0 when the folder can be used, 1 when it cannot.

Usage:
  python3 check_folder.py --dir ~/job-search
  python3 check_folder.py --dir ~/job-search --network
  python3 check_folder.py --dir ~/job-search --init
"""

from __future__ import annotations

import argparse
import http.client
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

from jobfiles import FolderError, job_folder, os_problem
from poll_boards import _jobs, fetch_json
from profile_yaml import ProfileError, get, load
from tailor_resume import MAC_SOFFICE

ASSETS = Path(__file__).resolve().parent.parent / "assets"
# What --init copies: (template in assets/, name in the folder).
TEMPLATES = (
    ("jobs.template.json", "jobs.json"),
    ("search-config.template.json", "search-config.json"),
    ("kanban.html", "kanban.html"),
)
FOLDERS = ("resumes", "backups", "outreach")
# What each missing file means, in the order they are listed.
EXPECTED = {
    "profile.yaml": "run intake to write it (references/intake.md)",
    "jobs.json": "--init creates it",
    "search-config.json": "--init creates it",
    "job-search.md": "the first run writes it",
    "kanban.html": "--init copies it",
    "resumes": "--init creates it",
    "backups": "--init creates it",
    "outreach": "--init creates it",
}
UPLOAD = "use upload mode (references/environments.md)"


class Check(NamedTuple):
    status: str  # OK, MISSING, FAIL or BLOCKED
    label: str
    note: str = ""


# --- the folder -------------------------------------------------------------------------------


def check_folder(root: Path) -> tuple[list[Check], bool]:
    """Can this agent use the folder? Return the lines to print and the answer."""
    if not root.exists():
        note = (
            f"{root} does not exist here. If it is on the person's computer and this agent "
            f"runs somewhere else, {UPLOAD}"
        )
        return [Check("FAIL", "folder exists", note)], False
    if not root.is_dir():
        return [Check("FAIL", "folder exists", f"{root} is a file, not a folder")], False
    lines = [Check("OK", "folder exists", str(root))]
    try:
        fd, probe = tempfile.mkstemp(dir=root, prefix=".job-scout-check-")
        os.close(fd)
        Path(probe).unlink()
    except OSError as exc:
        note = (
            f"cannot write in {root}: {exc.strerror or exc}. Ask the person to give this agent "
            f"write access, or {UPLOAD}"
        )
        return [*lines, Check("FAIL", "can write here", note), *check_files(root)], False
    return [*lines, Check("OK", "can write here"), *check_files(root)], True


def check_files(root: Path) -> list[Check]:
    lines = [
        Check("OK", name) if (root / name).exists() else Check("MISSING", name, hint)
        for name, hint in EXPECTED.items()
    ]
    profile = root / "profile.yaml"
    if not profile.is_file():
        return lines
    try:
        base = get(load(profile), "resume.base_docx")
    except (ProfileError, OSError) as exc:
        return [*lines, Check("FAIL", "profile.yaml", f"cannot be read: {exc}")]
    if base:
        path = Path(os.path.expanduser(str(base)))
        path = path if path.is_absolute() else root / path
        if path.is_file():
            lines.append(Check("OK", "base resume", str(path)))
        else:
            note = f"{base} not found: resume tailoring needs it"
            lines.append(Check("MISSING", "base resume", note))
    return lines


def init_folder(root: Path) -> list[str]:
    """Create the folder, its subfolders and the files copied from the templates.

    A file that is already there is kept as it is: each copy uses exclusive create, so it
    can never replace a file.
    """
    done = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        for name in FOLDERS:
            existed = (root / name).is_dir()
            (root / name).mkdir(exist_ok=True)
            done.append(f"{'kept' if existed else 'created'} {name}/")
    except OSError as exc:
        raise FolderError(os_problem(exc, "create", exc.filename)) from None
    for template, name in TEMPLATES:
        target = root / name
        try:
            with target.open("x", encoding="utf-8") as f:
                f.write((ASSETS / template).read_text(encoding="utf-8"))
        except FileExistsError:
            done.append(f"kept {name}")
            continue
        except OSError as exc:
            raise FolderError(os_problem(exc, "write", target)) from None
        done.append(f"created {name}")
    return done


# --- tools and network ---------------------------------------------------------------------------


def check_tools(which=shutil.which, has_module=None) -> list[Check]:
    if has_module is None:

        def has_module(name):
            return importlib.util.find_spec(name) is not None

    v = sys.version_info
    python = f"Python {v.major}.{v.minor}"
    lines = [
        Check("OK", python)
        if v >= (3, 9)
        else Check("FAIL", python, "the scripts need Python 3.9 or newer")
    ]
    if has_module("docx"):
        lines.append(Check("OK", "python-docx"))
    else:
        note = "needed for resume tailoring: python3 -m pip install python-docx"
        lines.append(Check("MISSING", "python-docx", note))
    if which("soffice") or which("libreoffice") or which(MAC_SOFFICE):
        lines.append(Check("OK", "LibreOffice"))
    else:
        note = "optional: without it, tailored resumes have no PDF"
        lines.append(Check("MISSING", "LibreOffice", note))
    if which("pdftotext"):
        lines.append(Check("OK", "pdftotext"))
    else:
        lines.append(Check("MISSING", "pdftotext", "optional: without it, PDFs are not checked"))
    return lines


def network_targets() -> dict[str, str]:
    """One URL per host that poll_boards.py fetches, built from the search config template."""
    config = json.loads((ASSETS / "search-config.template.json").read_text(encoding="utf-8"))
    starter = config.get("starter_boards") or {}
    # A host that answers 404 for a token that does not exist is still reachable.
    boards = {
        kind: (starter.get(kind) or [])[:1] or [{"token": "example"}]
        for kind in ("ashby", "greenhouse", "lever")
    }
    probe = {"boards": boards, "aggregators": config.get("aggregators") or {}}
    targets: dict[str, str] = {}
    for _, url, _, _ in _jobs(probe):
        targets.setdefault(urlparse(url).hostname, url)
    return targets


def check_network(fetch=fetch_json, timeout: float = 10.0) -> list[Check]:
    lines = []
    for host, url in network_targets().items():
        try:
            status, _ = fetch(url, timeout)
        except ValueError:
            note = "answered, but not with JSON: a proxy or a sign-in page may be in the way"
            lines.append(Check("BLOCKED", host, note))
            continue
        except (OSError, http.client.HTTPException) as exc:
            lines.append(Check("BLOCKED", host, f"no answer: {getattr(exc, 'reason', exc)}"))
            continue
        if status in (403, 407):
            note = f"HTTP {status}: a network filter may block this host"
            lines.append(Check("BLOCKED", host, note))
        else:
            lines.append(Check("OK", host, f"HTTP {status}"))
    return lines


# --- output ------------------------------------------------------------------------------------


def _print(title: str, lines: list[Check]) -> None:
    print(title)
    for line in lines:
        print(f"  {line.status:<8} {line.label}" + (f"  {line.note}" if line.note else ""))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument(
        "--init", action="store_true", help="create a new folder from the templates first"
    )
    p.add_argument(
        "--network", action="store_true", help="also check that the job board APIs answer"
    )
    p.add_argument("--timeout", type=float, default=10, help="seconds per network check")
    args = p.parse_args(argv)
    root = job_folder(args.dir)

    if args.init:
        try:
            for line in init_folder(root):
                print(line)
        except FolderError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print()
    folder, usable = check_folder(root)
    _print("Job search folder", folder)
    _print("Tools", check_tools())
    if args.network:
        _print("Network", check_network(timeout=args.timeout))
    if usable:
        print(
            "Result: this agent can use the folder. This check cannot tell whether the folder "
            "stays after this conversation: a chat app's sandbox can be written to and is "
            "still removed later. See references/environments.md."
        )
        return 0
    print(f"Result: this agent cannot use this folder. If the files are elsewhere, {UPLOAD}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

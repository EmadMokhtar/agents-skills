#!/usr/bin/env python3
"""Housekeeping for tailored resumes, driven by jobs.json. Preview by default; --apply writes.

1. ARCHIVE  A tailored resume whose role is 'rejected' or 'archived' is moved (never
            deleted) into resumes/_archive/, and the role's `resume` path is updated.
2. RESYNC   For roles that are 'new', a corrected date in the base resume (an employer
            line, education, a certification) is copied into the tailored copy. This carries
            a correction such as a wrong start month into the copies the user is about to
            send. Tailored text (summary, skills, bullets) is never touched.

Only dates change. A line is resynced when it has a month and a year in it ("Jan 2020"), and
the base has exactly one line whose words, with the dates removed, are the same. A line whose
words were tailored never matches, so it is never overwritten.

Resumes for 'applied' and 'in_process' roles are frozen: the employer already has that
version. They are reported, not changed. Use --resync-applied only when the user asks.

Usage:
  python3 sync_resumes.py --dir ~/job-search              # preview: changes nothing
  python3 sync_resumes.py --dir ~/job-search --apply      # archive and resync
  python3 sync_resumes.py --dir ~/job-search --apply --no-pdf

Lines to report to the user: MISSING, PDF FAILED, PDF STALE, PAGE COUNT, CANNOT RESYNC.
The exit code is 1 when any of them appears.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from jobfiles import FolderError, load_tracker, resolve_in, save_tracker, today_iso
from profile_yaml import ProfileError, get, load
from tailor_resume import (
    TailorError,
    check_pdf,
    expected_pages,
    need_docx,
    para_text,
    paragraphs,
    render_pdf,
    replace_span,
)

DEAD = ("rejected", "archived")
LIVE = ("new",)
SENT = ("applied", "in_process")
MONTHS = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
FACT_RE = re.compile(rf"\b{MONTHS}\s*\d{{4}}\b", re.I)
DATE_WORDS_RE = re.compile(rf"\b{MONTHS}\b|\b\d{{4}}\b|\b(present|current|now|today)\b", re.I)


def is_fact(text: str) -> bool:
    return bool(FACT_RE.search(text))


def anchor(text: str) -> str:
    """A paragraph's identity: all of its words, with dates and punctuation removed."""
    text = DATE_WORDS_RE.sub(" ", text.lower())
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def resync(path: Path, base_texts: list[str], apply: bool) -> tuple[list, list]:
    """Return (changes, problems). Each change is (old line, new line)."""
    document = need_docx()
    doc = document(str(path))
    base_by_anchor: dict[str, list[str]] = {}
    for t in base_texts:
        if t.strip():
            base_by_anchor.setdefault(anchor(t), []).append(t)
    mine: dict[str, list] = {}
    for p in paragraphs(doc):
        t = para_text(p)
        if t.strip():
            mine.setdefault(anchor(t), []).append(p)

    changes, problems = [], []
    for p in paragraphs(doc):
        old = para_text(p)
        if not old.strip() or not is_fact(old):
            continue
        key = anchor(old)
        if len(base_by_anchor.get(key, [])) != 1 or len(mine.get(key, [])) != 1:
            continue
        new = base_by_anchor[key][0]
        if new == old:
            continue
        old_parts, new_parts = old.split("\t"), new.split("\t")
        if len(old_parts) != len(new_parts):
            problems.append(f"CANNOT RESYNC  {path.name}: tab layout differs: {new[:60]!r}")
            continue
        changes.append((old, new))
        if apply:
            # Same length is checked above. zip(strict=) needs Python 3.10; these run on 3.9.
            for o, n in zip(old_parts, new_parts):  # noqa: B905
                if o != n and not replace_span(p, o, n):
                    problems.append(f"CANNOT RESYNC  {path.name}: could not place {n[:60]!r}")
    if apply and changes:
        doc.save(str(path))
    return changes, problems


def _resume_path(root: Path, stored: str | None) -> Path | None:
    if not stored:
        return None
    path = resolve_in(root, os.path.expanduser(stored))
    if path.exists():
        return path
    fallback = root / "resumes" / Path(stored).name
    return fallback if fallback.exists() else path


SUFFIXES = (".docx", ".pdf", ".edits.json")


def _archive_stem(archive_dir: Path, stem: str) -> str:
    """A file name stem that no archived file uses yet, so nothing is overwritten."""
    candidate, n = stem, 2
    while any((archive_dir / f"{candidate}{s}").exists() for s in SUFFIXES):
        candidate, n = f"{stem}-{n}", n + 1
    return candidate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument("--apply", action="store_true", help="move and rewrite files")
    p.add_argument(
        "--resync-applied", action="store_true", help="also resync applied and in_process roles"
    )
    p.add_argument("--no-pdf", action="store_true", help="do not re-render or check PDFs")
    p.add_argument("--base", help="the base resume (default: resume.base_docx)")
    p.add_argument("--today", help="override today's date, YYYY-MM-DD")
    args = p.parse_args(argv)
    try:
        document = need_docx()
        root = resolve_in(Path(args.dir), ".")
        today = today_iso(args.today)
        profile = load(root / "profile.yaml") if (root / "profile.yaml").exists() else {}
        base_name = args.base or get(profile, "resume.base_docx")
        if not base_name:
            raise TailorError("no base resume: set resume.base_docx in profile.yaml or pass --base")
        base = Path(os.path.expanduser(base_name))
        base = base if base.is_absolute() else root / base
        if not base.is_file():
            raise TailorError(f"base resume not found: {base}")
        data = load_tracker(root)
    except (TailorError, FolderError, ProfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    base_texts = [para_text(x) for x in paragraphs(document(str(base)))]
    pages = None if args.no_pdf else expected_pages(base, get(profile, "resume.page_count"))
    archive_dir = root / "resumes" / "_archive"
    failures, archived, resynced, frozen, clean = [], [], [], [], 0
    tracker_changed = False

    for job in data["jobs"]:
        try:
            path = _resume_path(root, job.get("resume"))
        except FolderError as exc:
            failures.append(f"MISSING  {job.get('id')}: {exc}")
            continue
        if path is None:
            continue
        label = f"{job.get('company')}: {str(job.get('title'))[:40]}"
        status = job.get("status")

        if status in DEAD:
            if path.exists() and archive_dir not in path.parents:
                archived.append(f"[{status}] {path.name}")
                if args.apply:
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    stem = _archive_stem(archive_dir, path.stem)
                    for suffix in SUFFIXES:
                        src = path.parent / f"{path.stem}{suffix}"
                        if src.exists():
                            shutil.move(str(src), str(archive_dir / f"{stem}{suffix}"))
                    job["resume"] = (archive_dir / f"{stem}.docx").relative_to(root).as_posix()
                    tracker_changed = True
            continue

        live = status in LIVE or (status in SENT and args.resync_applied)
        if not path.exists():
            if live:
                failures.append(f"MISSING  {label}: {path.name}")
            continue
        if not live:
            if status in SENT:
                changes, _ = resync(path, base_texts, apply=False)
                if changes:
                    frozen.append(f"{label} ({len(changes)} line(s) differ)")
            continue

        changes, problems = resync(path, base_texts, apply=args.apply)
        failures += problems
        pdf = path.with_suffix(".pdf")
        facts = [para_text(x) for x in paragraphs(document(str(path))) if is_fact(para_text(x))]
        stale = []
        if not args.no_pdf and pdf.exists():
            stale = [s for s in check_pdf(pdf, facts, None) if s.startswith("PDF STALE")]
        if not changes and not stale:
            clean += 1
            continue
        resynced.append((label, changes or [("(PDF out of date)", "re-render from the .docx")]))
        if args.apply and not args.no_pdf:
            try:
                rendered = render_pdf(path)
            except TailorError as exc:
                failures.append(f"{exc}")
                continue
            if rendered is None:
                print(f"note: LibreOffice is not installed; {pdf.name} was not re-rendered")
                continue
            failures += check_pdf(rendered, facts, pages)

    if tracker_changed:
        save_tracker(root, data, today)

    verb = "Moved" if args.apply else "Would move"
    print(f"== ARCHIVE == {verb} {len(archived)} resume(s) to resumes/_archive/")
    for line in archived[:40]:
        print(f"   {line}")
    if len(archived) > 40:
        print(f"   ... and {len(archived) - 40} more")
    verb = "Resynced" if args.apply else "Would resync"
    print(f"== RESYNC == {verb} {len(resynced)} live resume(s); {clean} already match the base")
    for label, changes in resynced:
        print(f"   {label}")
        for old, new in changes:
            print(f"      - {old[:90]!r}\n      + {new[:90]!r}")
    if frozen:
        print(f"== ALREADY APPLIED: not changed ({len(frozen)}) ==")
        print("   The employer has the version that was sent. Use --resync-applied only if asked.")
        for line in frozen:
            print(f"   {line}")
    for line in failures:
        print(line)
    if not args.apply:
        print("Preview only. Run again with --apply to make these changes.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Warn about documentation that has gone unreviewed, or unreviewed code.

Two checks, both advisory, neither able to fail a build:

  last_reviewed:  a page nobody has looked at in MAX_REVIEW_AGE_DAYS
  covers:         a path a page claims to describe changed, and the page
                  did not

The precise counterpart to scripts/check_docs_updated.py, which is the
blunt version of the second check and IS a hard gate. This one names the
page and the path; that one only knows that source moved and prose did not.

This check only warns. A large refactor trips path coupling across many pages
at once, which lands exactly when a team is busiest. Make it a failure only
when the warnings are rare and the team trusts them.

Needs only Python 3 and its standard library. Run it with `just docs-freshness`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DOCS_ROOT = Path("docs")

# adr/ is history. An accepted decision record does not go stale: it
# records what was decided, when, and why. Asking someone to re-review one
# twice a year trains them to ignore the warning, and superseding a
# decision means writing a NEW record, never editing the old one.
EXCLUDED_PREFIXES = ("docs/adr/",)

# Six months. Long enough that an actively maintained page is never
# flagged, short enough that a page nobody has opened in a release cycle
# is. Not tuned against anything -- adjust it once there is evidence.
MAX_REVIEW_AGE_DAYS = 180


@dataclass(frozen=True)
class Page:
    """A published page and the two hygiene claims its frontmatter makes."""

    path: str
    last_reviewed: dt.date | None
    covers: list[str] = field(default_factory=list)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """The front matter between the leading `---` fences, as a small dict.

    It reads only what this script needs, so it needs no YAML library: `last_reviewed:
    YYYY-MM-DD`, and a `covers:` list written as `- path` lines.

    Deliberately strict about the opening fence being the FIRST line: a `---` used as a
    horizontal rule mid-page is ordinary Markdown, and treating it as front matter would
    swallow the prose after it.
    """
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, Any] = {}
    key: str | None = None
    for line in text[4:end].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and key is not None and isinstance(meta.get(key), list):
            meta[key].append(stripped[2:].strip().strip("'\""))
            continue
        name, separator, value = line.partition(":")
        if not separator:
            continue
        key, value = name.strip(), value.strip().strip("'\"")
        meta[key] = value if value else []
    reviewed = meta.get("last_reviewed")
    if isinstance(reviewed, str):
        try:
            meta["last_reviewed"] = dt.date.fromisoformat(reviewed)
        except ValueError:
            del meta["last_reviewed"]  # malformed: treated as absent, never a crash
    return meta


def load_pages(
    root: Path = DOCS_ROOT, excluded_prefixes: Sequence[str] = EXCLUDED_PREFIXES
) -> list[Page]:
    """Every published page, with whatever frontmatter it carries.

    `excluded_prefixes` defaults to `EXCLUDED_PREFIXES`; the caller may add
    to it (for example a folder of design notes) via the `--exclude`
    command-line option.
    """
    pages: list[Page] = []
    for path in sorted(root.rglob("*.md")):
        as_posix = path.as_posix()
        if as_posix.startswith(tuple(excluded_prefixes)):
            continue
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        reviewed = meta.get("last_reviewed")
        covers = meta.get("covers") or []
        pages.append(
            Page(
                path=as_posix,
                # parse_frontmatter turns an ISO-8601 value into a date; anything
                # else is malformed and treated as absent rather than crashing an
                # advisory check.
                last_reviewed=reviewed if isinstance(reviewed, dt.date) else None,
                covers=[str(entry) for entry in covers],
            )
        )
    return pages


def stale_pages(pages: Iterable[Page], today: dt.date) -> list[Page]:
    """Pages whose review date is older than the maximum age.

    A page with NO review date is not stale -- it is undeclared, which is a
    different problem reported by its own warning. Conflating the two
    produces warnings citing dates that never existed.
    """
    cutoff = today - dt.timedelta(days=MAX_REVIEW_AGE_DAYS)
    return [
        page for page in pages if page.last_reviewed is not None and page.last_reviewed < cutoff
    ]


def undeclared_pages(pages: Iterable[Page]) -> list[Page]:
    """Published pages carrying no `last_reviewed` at all."""
    return [page for page in pages if page.last_reviewed is None]


def uncovered_changes(pages: Iterable[Page], changed: set[str]) -> list[tuple[str, str]]:
    """(page, covered path) pairs where the path moved and the page did not.

    A `covers:` entry ending in `/` matches every file beneath it. Listing
    files one by one would make the frontmatter unmaintainable, and
    unmaintainable frontmatter goes stale -- which is the failure this
    whole mechanism exists to catch.
    """
    findings: list[tuple[str, str]] = []
    for page in pages:
        if page.path in changed:
            continue
        for covered in page.covers:
            if any(
                path == covered or (covered.endswith("/") and path.startswith(covered))
                for path in changed
            ):
                findings.append((page.path, covered))
    return findings


def changed_files(base: str, head: str) -> set[str]:
    """Paths changed between `base` and `head`, as git reports them.

    `--relative` makes the paths relative to the CURRENT directory rather
    than the repository root, so the same `covers:` paths serve this
    script from any directory the project is checked out in, or from a
    subdirectory of a larger repository that vendors it -- neither run
    carries a prefix the other one does not.
    """
    completed = subprocess.run(
        ["git", "diff", "--name-only", "--relative", f"{base}...{head}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in completed.stdout.splitlines() if line}


def warn(path: str, message: str) -> None:
    """A GitHub Actions annotation, which is also readable as plain text."""
    print(f"::warning file={path}::{message}")


def main(argv: Sequence[str] | None = None) -> int:
    """Always returns 0. These checks advise; they never block."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PREFIX",
        help=(
            "exclude pages under this prefix from every check; repeatable, "
            f"added to the default {EXCLUDED_PREFIXES}"
        ),
    )
    parser.add_argument("base", help="the base ref of the range to check")
    parser.add_argument("head", help="the head ref of the range to check")
    args = parser.parse_args(argv)

    excluded_prefixes = (*EXCLUDED_PREFIXES, *(args.exclude or ()))

    pages = load_pages(excluded_prefixes=excluded_prefixes)
    changed = changed_files(args.base, args.head)
    today = dt.date.today()

    for page in stale_pages(pages, today=today):
        age = (today - page.last_reviewed).days  # type: ignore[operator]
        warn(
            page.path,
            f"last reviewed {page.last_reviewed} ({age} days ago, maximum "
            f"{MAX_REVIEW_AGE_DAYS}). Re-read it and update last_reviewed.",
        )

    for page in undeclared_pages(pages):
        warn(page.path, "no `last_reviewed` in its frontmatter.")

    for page_path, covered in uncovered_changes(pages, changed):
        warn(
            page_path,
            f"covers `{covered}`, which changed in this pull request while "
            f"this page did not. Check whether it is still accurate.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

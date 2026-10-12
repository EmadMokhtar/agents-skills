#!/usr/bin/env python3
"""Copy the repo-setup templates into a repository without overwriting anything.

Usage:
    scaffold.py TARGET --modules docs-site,docs-gates --set NAME="My Tool" ...
    scaffold.py TARGET --skip .github/workflows/release.yml --skip LICENSE ...
    scaffold.py --list

`base` is always included. For every template file the script does one of these:

    created   the file did not exist, so it was written
    same      the file exists and already has this content
    differs   the file exists with other content; it is left alone
    merged    the file is .gitignore; the missing lines were appended

The toolchain decides how the repository's own tools (hooks, workflow lint, docs build, release)
run. `uv` is for Python repositories: the tools are Python packages that uv runs. `native` is for
everything else: the tools are programs that each person installs (for example with Homebrew), CI
installs the same pinned versions, and the git hooks are plain scripts. A `native` repository gets
no uv, no pyproject.toml and no lock file. `--toolchain auto` (the default) picks `uv` when the
folder has a Python project file.

Placeholders look like __NAME__. The required values are NAME, SLUG, DESCRIPTION,
OWNER and AUTHOR. YEAR, TODAY, SITE_URL, BRANCH and SOURCE_PREFIX have defaults.
The script stops before writing anything if a placeholder has no value.

A file named `NAME.tmpl` is written as `NAME`.

One template can serve several module combinations. A block between marker lines is
kept only when its module is chosen:

    # @if docs-site          (in Markdown: <!-- @if docs-site -->)
    ...kept when docs-site is chosen...
    # @else
    ...kept when it is not...
    # @endif

The marker lines themselves never reach the output. A file whose whole content sits in a block
that is switched off comes out empty, and an empty file is not written.

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# module id -> (what it adds, modules it needs)
MODULES: dict[str, tuple[str, tuple[str, ...]]] = {
    "base": (
        "README, licence, pre-commit (hygiene, gitleaks, commit-message check), justfile, "
        "tooling pyproject, CI `checks`, PR title check, Dependabot, contributing guide",
        (),
    ),
    "release": (
        "releases with commitizen: bump, changelog, tag, GitHub Release (skip if another "
        "release tool is in use)",
        (),
    ),
    "agents": ("AGENTS.md, CLAUDE.md and Copilot review instructions", ()),
    "adr": ("decision records: template, index and five starter records", ()),
    "docs-site": (
        "MkDocs Material site, getting started, glossary, roadmap, Pages deploy",
        (),
    ),
    "docs-gates": (
        "docs-updated gate, docs freshness warnings, link checker",
        ("docs-site",),
    ),
    "nightly": ("scheduled run of every check, so a check that rots is noticed", ()),
    "security": ("dependency review on pull requests and a Trivy scan of the tree", ()),
    "container": (
        "multi-architecture image build, Trivy image scan, SBOM, publish to GHCR on release",
        ("security", "release"),
    ),
}
# Names that `@if` accepts besides the modules:
#   licensed  true unless --license none
#   uv        true with --toolchain uv
#   native    true with --toolchain native
#   ciextras  true when docs-gates, security or container is installed: CI then runs gates
#             that need GitHub or the network and so are not part of `just check`
PSEUDO_MODULES = ("licensed", "uv", "native", "ciextras")
TOOLCHAINS = ("auto", "uv", "native")
PYTHON_MARKERS = ("pyproject.toml", "uv.lock", "requirements.txt", "setup.py", "Pipfile")

REQUIRED = ("NAME", "SLUG", "DESCRIPTION", "OWNER", "AUTHOR")
# Free text lands inside "double quotes" in YAML and TOML, so these characters are refused.
FREE_TEXT = ("NAME", "DESCRIPTION", "AUTHOR", "SOURCE_PREFIX")
UNSAFE_TEXT_RE = re.compile(r'["\\\r\n]')
# The patterns are used with fullmatch: `$` would accept a trailing line break.
# SLUG and OWNER end up in URLs and names, so they cannot hold a slash. A branch name can.
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
# A source folder is written into a shell command, so it may hold path characters only.
SOURCE_PREFIX_RE = re.compile(r"[A-Za-z0-9._/-]+")
PLACEHOLDER_RE = re.compile(r"__([A-Z][A-Z0-9_]*)__")
MARKER_RE = re.compile(
    r"^\s*(?:#|<!--)\s*@(?P<kind>if|else|endif)(?:\s+(?P<module>[a-z][a-z-]*))?\s*(?:-->)?\s*$"
)
LICENSES = ("MIT", "Apache-2.0", "MPL-2.0", "Proprietary", "none")
MERGE_APPEND = {".gitignore"}


@dataclass
class Result:
    status: str
    path: str
    note: str = ""


def detect_toolchain(target: Path) -> str:
    """`uv` for a Python repository, `native` for everything else.

    A repository that is not Python (Go, Node, Rust, empty) must not get uv, a pyproject.toml,
    a uv.lock or a .python-version just so that the repository's tools can run.
    """
    return "uv" if any((target / name).exists() for name in PYTHON_MARKERS) else "native"


def build_values(pairs: list[str], license_id: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise SystemExit(f"error: --set needs KEY=VALUE, got {pair!r}")
        values[key.strip().upper()] = value
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise SystemExit("error: missing --set values for: " + ", ".join(missing))
    for key in FREE_TEXT:
        if UNSAFE_TEXT_RE.search(values.get(key, "")):
            raise SystemExit(
                f"error: {key} must not contain a double quote, a backslash or a line break"
            )
    for key, pattern in (("SLUG", IDENTIFIER_RE), ("OWNER", IDENTIFIER_RE), ("BRANCH", BRANCH_RE)):
        if key in values and not pattern.fullmatch(values[key]):
            allowed = "letters, digits, dots, dashes, underscores" + (
                " and slashes" if pattern is BRANCH_RE else ""
            )
            raise SystemExit(f"error: {key} must be {allowed}")
    today = dt.date.today()
    values.setdefault("YEAR", str(today.year))
    values.setdefault("TODAY", today.isoformat())
    values.setdefault("BRANCH", "main")
    values.setdefault("SOURCE_PREFIX", "src/")
    prefixes = [p.strip() for p in values["SOURCE_PREFIX"].split(",") if p.strip()]
    # A prefix is compared with the start of each changed path, so `src` would also match
    # `src-old/`. Each one must therefore end in a slash.
    bad = [p for p in prefixes if not SOURCE_PREFIX_RE.fullmatch(p) or not p.endswith("/")]
    if bad or not prefixes:
        raise SystemExit(
            "error: SOURCE_PREFIX must be folders ending in a slash, such as src/ or "
            "cmd/,internal/ (letters, digits, dots, dashes, underscores and slashes only); "
            f"got {values['SOURCE_PREFIX']!r}"
        )
    values["SOURCE_ARGS"] = " ".join(f"--source '{p}'" for p in prefixes)
    values["SOURCE_TEXT"] = " or ".join(f"`{p}`" for p in prefixes)
    values.setdefault("SITE_URL", f"https://{values['OWNER'].lower()}.github.io/{values['SLUG']}/")
    values["LICENSE"] = license_id
    values["OWNER_LOWER"] = values["OWNER"].lower()
    return values


def select_blocks(text: str, modules: set[str], where: str) -> str:
    """Drop the marker lines, and the blocks whose module is not chosen."""
    out: list[str] = []
    stack: list[bool] = []  # one entry per open @if: is this branch kept?
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        marker = MARKER_RE.match(line.rstrip("\n"))
        if marker is None:
            if all(stack):
                out.append(line)
            continue
        kind, module = marker["kind"], marker["module"]
        if kind == "if":
            if module not in MODULES and module not in PSEUDO_MODULES:
                raise SystemExit(f"error: {where}:{number}: unknown module {module!r} in @if")
            stack.append(module in modules)
        elif not stack:
            raise SystemExit(f"error: {where}:{number}: @{kind} without @if")
        elif kind == "else":
            stack[-1] = not stack[-1]
        else:
            stack.pop()
    if stack:
        raise SystemExit(f"error: {where}: @if without @endif")
    return "".join(out)


def render(text: str, values: dict[str, str], modules: set[str], where: str) -> str:
    text = select_blocks(text, modules, where)
    return PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def plan(modules: list[str], license_id: str, skip: list[str]) -> list[tuple[Path, str]]:
    """Every (source file, target path) pair for the chosen modules, minus `skip` patterns."""
    pairs: list[tuple[Path, str]] = []
    for module in modules:
        root = ASSETS / module
        if not root.is_dir():
            raise SystemExit(f"error: module {module!r} has no assets folder")
        for source in sorted(p for p in root.rglob("*") if p.is_file()):
            # `*.tmpl` files keep a name that no tool reacts to while they sit in the skill
            # (a nested AGENTS.md or CLAUDE.md would be loaded by agents working here).
            pairs.append((source, source.relative_to(root).as_posix().removesuffix(".tmpl")))
    if license_id != "none":
        pairs.append((ASSETS / "licenses" / license_id, "LICENSE"))
    return [(src, rel) for src, rel in pairs if not any(fnmatch.fnmatch(rel, pat) for pat in skip)]


def symlink_in_path(target: Path, rel: str) -> str | None:
    """The first symlink on the way from `target` to `rel`, or None.

    `Path.exists()` is False for a dangling symlink, and `write_text` follows the link, so a
    check that relies on `exists()` could write outside the repository. Any symlink on the path,
    in the file or in a parent folder, is refused.
    """
    current = target
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            return current.relative_to(target).as_posix()
    return None


def apply(
    target: Path,
    pairs: list[tuple[Path, str]],
    values: dict[str, str],
    modules: set[str],
    dry_run: bool,
    show_diff: bool,
) -> tuple[list[Result], list[str]]:
    # Render everything first, so a missing value stops the run before any write.
    rendered = [
        (src, rel, render(src.read_text(encoding="utf-8"), values, modules, rel))
        for src, rel in pairs
    ]
    bad = sorted(
        f"{rel}: {', '.join(sorted(set(PLACEHOLDER_RE.findall(body))))}"
        for _, rel, body in rendered
        if PLACEHOLDER_RE.search(body)
    )
    if bad:
        raise SystemExit("error: placeholders with no value:\n  " + "\n  ".join(bad))
    linked = sorted(
        f"{rel} (through {link})"
        for _, rel, body in rendered
        if body.strip() and (link := symlink_in_path(target, rel))
    )
    if linked:
        raise SystemExit(
            "error: refusing to write through a symlink; nothing was written:\n  "
            + "\n  ".join(linked)
        )

    results: list[Result] = []
    diffs: list[str] = []
    for source, rel, body in rendered:
        if not body.strip():
            continue  # a template wrapped in an `@if` for a module that is not chosen
        dest = target / rel
        if not dest.exists():
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(body, encoding="utf-8")
                dest.chmod(source.stat().st_mode & 0o777)
            results.append(Result("created", rel))
            continue
        existing = dest.read_text(encoding="utf-8")
        if existing == body:
            results.append(Result("same", rel))
        elif rel in MERGE_APPEND:
            have = set(existing.splitlines())
            add = [line for line in body.splitlines() if line.strip() and line not in have]
            if add and not dry_run:
                separator = "" if existing.endswith("\n") or not existing else "\n"
                with dest.open("a", encoding="utf-8") as handle:
                    handle.write(separator + "\n# Added by repo-setup\n" + "\n".join(add) + "\n")
            results.append(Result("merged", rel, f"+{len(add)} lines"))
        else:
            results.append(Result("differs", rel, "exists with other content; left alone"))
            if show_diff:
                diffs.append(
                    "".join(
                        difflib.unified_diff(
                            existing.splitlines(keepends=True),
                            body.splitlines(keepends=True),
                            fromfile=f"{rel} (yours)",
                            tofile=f"{rel} (template)",
                        )
                    )
                )
    return results, diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("target", nargs="?", type=Path, help="the repository folder")
    parser.add_argument("--modules", default="", help="comma-separated; `base` is always added")
    parser.add_argument("--set", dest="pairs", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--license", default="MIT", choices=LICENSES)
    parser.add_argument(
        "--toolchain",
        default="auto",
        choices=TOOLCHAINS,
        help="how the repository's tools run: uv (Python repositories) or native (tools"
        " installed on the machine, no Python project). auto picks uv when the folder has a"
        " Python project file, otherwise native",
    )
    parser.add_argument(
        "--skip", action="append", default=[], metavar="GLOB", help="do not create matching paths"
    )
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    parser.add_argument("--diff", action="store_true", help="show how each `differs` file differs")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--list", action="store_true", help="list the modules and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, (what, needs) in MODULES.items():
            extra = f" (needs {', '.join(needs)})" if needs else ""
            print(f"{name:11} {what}{extra}")
        return 0
    if args.target is None:
        parser.error("TARGET is required")
    if not args.target.is_dir():
        raise SystemExit(f"error: {args.target} is not a folder")
    if args.target.is_symlink():
        # is_dir() follows a symlink, and the checks in apply() look only below the target.
        raise SystemExit(
            f"error: {args.target} is a symlink; nothing was written. "
            f"Pass the real folder instead: {args.target.resolve()}"
        )
    # A link higher up the path (/tmp is one on macOS) is the caller's choice. Resolving it once
    # means every write and every symlink check below happens under the real folder.
    args.target = args.target.resolve()

    chosen = ["base", *[m for m in args.modules.split(",") if m and m != "base"]]
    for module in chosen:
        if module not in MODULES:
            raise SystemExit(f"error: unknown module {module!r}; try --list")
        for need in MODULES[module][1]:
            if need not in chosen:
                raise SystemExit(f"error: module {module!r} needs {need!r}")

    toolchain = detect_toolchain(args.target) if args.toolchain == "auto" else args.toolchain
    flags = {*chosen, toolchain}
    if {"docs-gates", "security", "container"} & set(chosen):
        flags.add("ciextras")
    if args.license != "none":
        flags.add("licensed")

    values = build_values(args.pairs, args.license)
    results, diffs = apply(
        args.target,
        plan([*chosen, f"toolchain-{toolchain}"], args.license, args.skip),
        values,
        flags,
        args.dry_run,
        args.diff,
    )

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        print(f"toolchain: {toolchain}\n")
        for r in results:
            print(f"{r.status:8} {r.path}" + (f"  ({r.note})" if r.note else ""))
        counts = {s: sum(r.status == s for r in results) for s in {r.status for r in results}}
        print("\n" + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
        created = [r.path for r in results if r.status == "created"]
        if created and not args.dry_run:
            # Stage and pin only what was created: the user's own files must stay as they are.
            print("\nstage the new files:  git add -- " + " ".join(created))
            # Workflows and the local setup action both carry pinned `uses:` lines.
            workflows = [
                p for p in created if p.startswith((".github/workflows/", ".github/actions/"))
            ]
            if workflows:
                print("pin the new actions:  pin_actions.py " + " ".join(workflows))
    for diff in diffs:
        print("\n" + diff)
    return 0


if __name__ == "__main__":
    sys.exit(main())

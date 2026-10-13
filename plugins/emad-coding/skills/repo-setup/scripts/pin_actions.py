#!/usr/bin/env python3
"""Pin every GitHub Action in a workflow to a full commit SHA.

Usage:
    pin_actions.py [--check] PATH [PATH ...]

A PATH is a workflow file, or a folder that is searched for *.yml and *.yaml.

A line such as

    - uses: actions/checkout@v7

becomes

    - uses: actions/checkout@<40 hex characters>  # v7.0.1

The script picks the newest stable release with the same major version as the
current ref. When the ref is already a SHA, the major version comes from the
trailing comment (`# v7.0.1`). That makes the command safe to run again: it
refreshes old pins and leaves current ones alone.

Why pin by SHA: a tag can be moved to different code after you reviewed it. A
commit SHA cannot.

With --check nothing is written. The script lists every action that is not
pinned to the newest SHA and exits with 1.

Needs `git` and network access to github.com. It uses no GitHub token.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

USES_RE = re.compile(
    r"^(?P<head>\s*(?:-\s+)?uses:\s+)"
    r"(?P<action>[\w.-]+/[\w.-]+(?:/[\w./-]+)?)"
    r"@(?P<ref>[^\s#]+)"
    r"(?P<comment>\s*#.*)?$"
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TAG_RE = re.compile(r"^v?(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?$")


def parse_uses(line: str) -> re.Match[str] | None:
    """Match a `uses: owner/repo@ref` line. Local and docker:// actions do not match."""
    return USES_RE.match(line.rstrip("\n"))


def parse_tags(ls_remote_output: str) -> dict[str, str]:
    """Map each tag name to the commit SHA it points at.

    `git ls-remote --tags` lists an annotated tag twice: once for the tag object,
    and once with a `^{}` suffix for the commit behind it. The commit is the one we
    want, so the suffixed line wins.
    """
    tags: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in ls_remote_output.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            peeled[name.removesuffix("^{}")] = sha
        else:
            tags[name] = sha
    tags.update(peeled)
    return tags


def _version_key(tag: str) -> tuple[int, int, int]:
    match = TAG_RE.match(tag)
    if match is None:  # Not a stable version tag. It sorts below every real one.
        return (-1, 0, 0)
    return (
        int(match["major"]),
        int(match["minor"] or 0),
        int(match["patch"] or 0),
    )


def latest_for_major(tags: dict[str, str], major: int) -> tuple[str, str] | None:
    """The newest stable tag with this major version, as (tag, sha).

    Tags with a suffix such as `-beta.1` do not match TAG_RE, so they are never
    chosen. A full `v7.0.1` tag is preferred over the floating `v7` tag.
    """
    candidates = [tag for tag in tags if TAG_RE.match(tag) and _version_key(tag)[0] == major]
    if not candidates:
        return None
    best = max(candidates, key=lambda tag: (_version_key(tag), tag.count(".")))
    return best, tags[best]


def hint_major(ref: str, comment: str | None) -> int | None:
    """The major version a ref stands for: from the tag itself, or from `# v7.0.1`."""
    if not SHA_RE.match(ref):
        match = TAG_RE.match(ref)
        return int(match["major"]) if match else None
    if comment:
        match = TAG_RE.match(comment.strip().lstrip("#").strip().split()[0])
        if match:
            return int(match["major"])
    return None


def fetch_tags(repo: str) -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", f"https://github.com/{repo}.git"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cannot list tags of {repo}: {result.stderr.strip()}")
    return parse_tags(result.stdout)


def workflow_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files += sorted([*path.rglob("*.yml"), *path.rglob("*.yaml")])
        else:
            files.append(path)
    return files


def pin_file(path: Path, cache: dict[str, dict[str, str]], check: bool) -> list[str]:
    """Pin one file. Returns one message per problem or change."""
    messages: list[str] = []
    out: list[str] = []
    changed = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(keepends=True), 1):
        match = parse_uses(line)
        if match is None:
            out.append(line)
            continue
        action, ref, comment = match["action"], match["ref"], match["comment"]
        repo = "/".join(action.split("/")[:2])
        major = hint_major(ref, comment)
        where = f"{path}:{number}: {action}@{ref[:12]}"
        if major is None:
            messages.append(f"{where}: cannot tell which major version to follow; pin it by hand")
            out.append(line)
            continue
        if repo not in cache:
            cache[repo] = fetch_tags(repo)
        found = latest_for_major(cache[repo], major)
        if found is None:
            messages.append(f"{where}: no stable v{major} release found")
            out.append(line)
            continue
        tag, sha = found
        if ref == sha:
            out.append(line)
            continue
        newline = "\n" if line.endswith("\n") else ""
        out.append(f"{match['head']}{action}@{sha}  # {tag}{newline}")
        changed = True
        messages.append(f"{where} -> {sha[:12]} # {tag}")
    if changed and not check:
        path.write_text("".join(out), encoding="utf-8")
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if any pin is not current"
    )
    args = parser.parse_args(argv)

    cache: dict[str, dict[str, str]] = {}
    messages: list[str] = []
    try:
        for path in workflow_files(args.paths):
            messages += pin_file(path, cache, args.check)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for message in messages:
        print(message)
    if not messages:
        print("every action is pinned to the newest release of its major version")
    return 1 if (args.check and messages) else 0


if __name__ == "__main__":
    raise SystemExit(main())

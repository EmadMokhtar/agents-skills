"""Decide which skills the Evals workflow evaluates.

Run: uv run python scripts/changed_skills.py --target all
     uv run python scripts/changed_skills.py --target emad-coding/conventional-commits
     uv run python scripts/changed_skills.py --base <sha> --head <sha>

It prints a JSON list of skill folders. A skill counts as changed when any
file under its folder changed, including its eval files. Deleted skills are
left out.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

from repo_model import REPO_ROOT, plugin_dirs, skill_dirs

USAGE = "use <plugin>/<skill> or 'all'"


def all_skills(root: Path) -> list[str]:
    return [s.relative_to(root).as_posix() for p in plugin_dirs(root) for s in skill_dirs(p)]


def skills_from_target(root: Path, target: str) -> list[str]:
    if target == "all":
        return all_skills(root)
    plugin, sep, skill = target.partition("/")
    path = f"plugins/{plugin}/skills/{skill}"
    if not (sep and plugin and skill and (root / path / "SKILL.md").is_file()):
        raise ValueError(f"no skill at {path}; {USAGE}")
    return [path]


def skills_from_changed_files(root: Path, files: list[str]) -> list[str]:
    found = set()
    for name in files:
        parts = PurePosixPath(name).parts
        if len(parts) >= 5 and parts[0] == "plugins" and parts[2] == "skills":
            path = "/".join(parts[:4])
            if (root / path / "SKILL.md").is_file():
                found.add(path)
    return sorted(found)


def git_changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the skills to evaluate, as JSON.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target", help="<plugin>/<skill>, or 'all'")
    group.add_argument("--base", help="base commit of a pull request")
    parser.add_argument("--head", default="HEAD", help="head commit of a pull request")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.target is not None:
            skills = skills_from_target(args.root, args.target)
        else:
            skills = skills_from_changed_files(args.root, git_changed_files(args.base, args.head))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(skills))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check the repository rules that no external validator knows about.

Run: just layout   (or: uv run python scripts/check_layout.py)
It prints one line per problem and exits with 1 when there is any problem.

Other tools own the other rules, so this script does not repeat them:
- `agentskills validate` checks each SKILL.md against the Agent Skills spec;
- `check-jsonschema` and `claude plugin validate` check the manifests too.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from repo_model import (
    PLUGIN_NAME_RE,
    RELEASE_CONFIG,
    RELEASE_MANIFEST,
    REPO_ROOT,
    SCHEMA_PATH,
    VERSION_UPDATER,
    RepoError,
    plugin_dirs,
    read_manifest,
    read_skill,
    skill_dirs,
)

MAX_SKILL_LINES = 500
# Top-level folders that never hold real skills. Folders whose name starts
# with "." (.git, .venv, .claude, ...) are always skipped.
SKIPPED_TOP_LEVEL = {"tests", "site", "node_modules"}


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def check_release_config(root: Path) -> list[str]:
    """Every plugin is a release-please package whose version matches plugin.json."""
    try:
        config = json.loads((root / RELEASE_CONFIG).read_text(encoding="utf-8"))
        versions = json.loads((root / RELEASE_MANIFEST).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{RELEASE_CONFIG} / {RELEASE_MANIFEST}: cannot read: {exc}"]
    packages = config.get("packages", {})
    problems: list[str] = []
    on_disk: set[str] = set()
    for plugin_dir in plugin_dirs(root):
        key = f"plugins/{plugin_dir.name}"
        on_disk.add(key)
        package = packages.get(key)
        if package is None:
            problems.append(
                f"{RELEASE_CONFIG}: {key} is not registered; `just new-plugin` does this"
            )
        else:
            if package.get("component") != plugin_dir.name:
                problems.append(f"{RELEASE_CONFIG}: {key} must have component {plugin_dir.name!r}")
            if VERSION_UPDATER not in package.get("extra-files", []):
                problems.append(
                    f"{RELEASE_CONFIG}: {key} must update plugin.json with {VERSION_UPDATER}"
                )
        if key not in versions:
            problems.append(f"{RELEASE_MANIFEST}: {key} has no version")
            continue
        try:
            plugin_version = read_manifest(plugin_dir).get("version")
        except RepoError:
            continue  # check_plugin already reports this
        if versions[key] != plugin_version:
            problems.append(
                f"{RELEASE_MANIFEST}: {key} is {versions[key]!r} but plugin.json says "
                f"{plugin_version!r}"
            )
    for key in sorted((set(packages) | set(versions)) - on_disk):
        problems.append(f"release-please: {key} is registered but plugins/ has no such folder")
    return problems


def find_problems(root: Path = REPO_ROOT, schema_path: Path = SCHEMA_PATH) -> list[str]:
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    problems: list[str] = []
    owners: dict[str, str] = {}  # skill name -> the first plugin that uses it
    for plugin_dir in plugin_dirs(root):
        problems += check_plugin(plugin_dir, root, validator)
        for skill_dir in skill_dirs(plugin_dir):
            problems += check_skill(skill_dir, root, owners)
    problems += check_skill_file_locations(root)
    problems += check_release_config(root)
    problems += check_readme(root)
    return problems


def check_plugin(plugin_dir: Path, root: Path, validator: Draft202012Validator) -> list[str]:
    where = _rel(plugin_dir / "plugin.json", root)
    try:
        manifest = read_manifest(plugin_dir)
    except RepoError as exc:
        return [f"{where}: {exc.reason}"]
    problems = [
        f"{where}: {error.message}"
        for error in sorted(validator.iter_errors(manifest), key=lambda e: e.message)
    ]
    if manifest.get("name") != plugin_dir.name:
        problems.append(
            f"{where}: name {manifest.get('name')!r} must equal the folder name {plugin_dir.name!r}"
        )
    if not PLUGIN_NAME_RE.match(plugin_dir.name):
        problems.append(
            f"{where}: folder name {plugin_dir.name!r} must match {PLUGIN_NAME_RE.pattern}"
        )
    for field in ("version", "description", "author"):
        if field not in manifest:
            problems.append(f"{where}: {field!r} is required in this repository")
    if "extensions" in manifest:
        problems.append(
            f"{where}: remove 'extensions'; Claude Code warns about it and --strict fails"
        )
    author = manifest.get("author")
    if isinstance(author, dict) and "email" in author:
        problems.append(f"{where}: remove author.email; this repository is public")
    if not skill_dirs(plugin_dir):
        problems.append(f"{_rel(plugin_dir, root)}: has no skills; add one with `just new-skill`")
    return problems


def check_skill(skill_dir: Path, root: Path, owners: dict[str, str]) -> list[str]:
    plugin = skill_dir.parent.parent.name
    where = _rel(skill_dir / "SKILL.md", root)
    problems: list[str] = []
    first_owner = owners.setdefault(skill_dir.name, plugin)
    if first_owner != plugin:
        problems.append(
            f"{_rel(skill_dir, root)}: skill name {skill_dir.name!r} is already used by plugin "
            f"{first_owner!r}; skill names must be unique across all plugins"
        )
    try:
        skill = read_skill(skill_dir, plugin)
    except RepoError as exc:
        return [*problems, f"{where}: {exc.reason}"]
    if skill.frontmatter.get("license") != "MIT":
        problems.append(f"{where}: frontmatter must have 'license: MIT'")
    if str(skill.frontmatter.get("description", "")).strip().upper().startswith("TODO"):
        problems.append(f"{where}: description is still the scaffold placeholder")
    lines = skill.text.count("\n")
    if lines >= MAX_SKILL_LINES:
        problems.append(
            f"{where}: {lines} lines; keep SKILL.md under {MAX_SKILL_LINES} lines "
            "and move detail into references/"
        )
    return problems


def check_readme(root: Path) -> list[str]:
    """README.md is the landing page, so it must list every plugin."""
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md: missing"]
    text = readme.read_text(encoding="utf-8")
    return [
        f"README.md: plugin `{d.name}` is missing from the plugin list"
        for d in plugin_dirs(root)
        if f"`{d.name}`" not in text
    ]


def check_skill_file_locations(root: Path) -> list[str]:
    """Report every SKILL.md that is not at plugins/<plugin>/skills/<skill>/SKILL.md."""
    problems: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        at_top = here == root
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and not (at_top and d in SKIPPED_TOP_LEVEL)
        )
        if "SKILL.md" not in filenames:
            continue
        parts = (here / "SKILL.md").relative_to(root).parts
        if len(parts) == 5 and parts[0] == "plugins" and parts[2] == "skills":
            continue
        problems.append(
            f"{'/'.join(parts)}: SKILL.md must sit at plugins/<plugin>/skills/<skill>/SKILL.md"
        )
    return problems


def main() -> int:
    problems = find_problems()
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} problem(s) found.", file=sys.stderr)
        return 1
    print("layout: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

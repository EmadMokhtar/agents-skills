"""Read the plugins and skills in this repository.

Every script and test reads the repository through this module, so the
layout rules live in one place:
- each plugin is a folder under plugins/ with a plugin.json file;
- each skill is a folder exactly one level under plugins/<plugin>/skills/
  with a SKILL.md file (Agent Plugins 1.0.0, section 7.1).
Names that start with "." (such as .DS_Store) are never plugins or skills.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "agent-plugins" / "1.0.0" / "plugin.schema.json"
MARKETPLACE_NAME = "emad-skills"
GITHUB_REPO = "EmadMokhtar/agents-skills"
REPO_URL = f"https://github.com/{GITHUB_REPO}"
SITE_URL = "https://emadmokhtar.github.io/agents-skills/"
OWNER = {"name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar"}
PLUGIN_NAME_RE = re.compile(r"^emad-[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
RELEASE_CONFIG = "release-please-config.json"
RELEASE_MANIFEST = ".release-please-manifest.json"
# The release-please updater that bumps "version" inside each plugin.json.
VERSION_UPDATER = {"type": "json", "path": "plugin.json", "jsonpath": "$.version"}


class RepoError(Exception):
    """A file in the repository is missing or invalid."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


class SkillFileError(ValueError):
    """The text of a SKILL.md file has no valid YAML frontmatter."""


@dataclass(frozen=True)
class Plugin:
    name: str
    path: Path
    manifest: dict


@dataclass(frozen=True)
class Skill:
    name: str
    plugin: str
    path: Path
    frontmatter: dict
    body: str
    text: str
    readme: str | None


def parse_skill_md(text: str) -> tuple[dict, str]:
    """Split a SKILL.md text into its frontmatter mapping and its body."""
    text = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    if not text.startswith("---\n"):
        raise SkillFileError("must start with a '---' line that opens the YAML frontmatter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise SkillFileError("has no '---' line that closes the YAML frontmatter")
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise SkillFileError(f"frontmatter is not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise SkillFileError("frontmatter must be a YAML mapping")
    return data, text[end + 5 :]


def _visible_dirs(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    return sorted(p for p in parent.iterdir() if p.is_dir() and not p.name.startswith("."))


def plugin_dirs(root: Path) -> list[Path]:
    return _visible_dirs(root / "plugins")


def skill_dirs(plugin_dir: Path) -> list[Path]:
    return _visible_dirs(plugin_dir / "skills")


def read_manifest(plugin_dir: Path) -> dict:
    path = plugin_dir / "plugin.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RepoError(path, "missing") from exc
    except json.JSONDecodeError as exc:
        raise RepoError(path, f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RepoError(path, "must contain a JSON object")
    return data


def read_skill(skill_dir: Path, plugin: str) -> Skill:
    path = skill_dir / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RepoError(path, "missing") from exc
    try:
        frontmatter, body = parse_skill_md(text)
    except SkillFileError as exc:
        raise RepoError(path, str(exc)) from exc
    readme_path = skill_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None
    return Skill(
        name=skill_dir.name,
        plugin=plugin,
        path=skill_dir,
        frontmatter=frontmatter,
        body=body,
        text=text,
        readme=readme,
    )


def load_plugins(root: Path = REPO_ROOT) -> list[Plugin]:
    return [Plugin(name=d.name, path=d, manifest=read_manifest(d)) for d in plugin_dirs(root)]


def load_skills(root: Path = REPO_ROOT) -> list[Skill]:
    return [read_skill(s, p.name) for p in plugin_dirs(root) for s in skill_dirs(p)]


def render_json(data: object) -> str:
    """The one JSON style for every file the scripts write."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(data), encoding="utf-8")

"""Shared test helpers: build a small fake repository in a temporary folder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from repo_model import RELEASE_CONFIG, RELEASE_MANIFEST, SCHEMA_ID, VERSION_UPDATER


class FakeRepo:
    """A throwaway repository tree. It passes every check unless a test breaks it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "plugins").mkdir()
        (root / "README.md").write_text("# agents-skills\n\n", encoding="utf-8")
        self._write_json(RELEASE_CONFIG, {"release-type": "simple", "packages": {}})
        self._write_json(RELEASE_MANIFEST, {})

    def _write_json(self, rel: str, data: object) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_json(self, rel: str) -> dict:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def add_plugin(self, name: str, **fields: object) -> Path:
        manifest = {
            "$schema": SCHEMA_ID,
            "name": name,
            "version": "0.0.0",
            "description": f"Skills for {name}.",
            "author": {"name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar"},
            "license": "MIT",
            **fields,
        }
        plugin_dir = self.root / "plugins" / name
        (plugin_dir / "skills").mkdir(parents=True)
        self._write_json(f"plugins/{name}/plugin.json", manifest)
        with (self.root / "README.md").open("a", encoding="utf-8") as f:
            f.write(f"- `{name}`\n")
        config = self._read_json(RELEASE_CONFIG)
        config["packages"][f"plugins/{name}"] = {
            "component": name,
            "extra-files": [dict(VERSION_UPDATER)],
        }
        self._write_json(RELEASE_CONFIG, config)
        versions = self._read_json(RELEASE_MANIFEST)
        versions[f"plugins/{name}"] = manifest["version"]
        self._write_json(RELEASE_MANIFEST, versions)
        return plugin_dir

    def add_skill(
        self,
        plugin: str,
        name: str,
        *,
        frontmatter: dict | None = None,
        body: str = "Do the thing.\n",
        readme: str | None = None,
    ) -> Path:
        if frontmatter is None:
            frontmatter = {
                "name": name,
                "description": f"Use when testing {name}.",
                "license": "MIT",
            }
        skill_dir = self.root / "plugins" / plugin / "skills" / name
        skill_dir.mkdir(parents=True)
        text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n" + body
        (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
        if readme is not None:
            (skill_dir / "README.md").write_text(readme, encoding="utf-8")
        return skill_dir


@pytest.fixture
def repo(tmp_path: Path) -> FakeRepo:
    return FakeRepo(tmp_path)

"""Create a new plugin folder and register it everywhere it must appear.

Run: just new-plugin <name> "<one-line description>"

It writes plugins/<name>/plugin.json, registers the plugin with
release-please, and regenerates both catalogs. Adding the plugin to the
README table stays a manual step, because that text is written for people.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repo_model import (
    OWNER,
    PLUGIN_NAME_RE,
    RELEASE_CONFIG,
    RELEASE_MANIFEST,
    REPO_ROOT,
    REPO_URL,
    SCHEMA_ID,
    SITE_URL,
    VERSION_UPDATER,
    write_json,
)
from sync_catalogs import write_catalogs

# "Not released yet". The first `feat` release turns it into 0.1.0.
INITIAL_VERSION = "0.0.0"


class ScaffoldError(Exception):
    """The requested plugin or skill cannot be created."""


def create_plugin(root: Path, name: str, description: str) -> Path:
    if not PLUGIN_NAME_RE.match(name):
        raise ScaffoldError(f"plugin name {name!r} must match {PLUGIN_NAME_RE.pattern}")
    if not description.strip():
        raise ScaffoldError("description must not be empty")
    plugin_dir = root / "plugins" / name
    if plugin_dir.exists():
        raise ScaffoldError(f"plugins/{name} already exists")
    config_path = root / RELEASE_CONFIG
    versions_path = root / RELEASE_MANIFEST
    config = json.loads(config_path.read_text(encoding="utf-8"))
    versions = json.loads(versions_path.read_text(encoding="utf-8"))

    # Every check passed: from here on, write.
    (plugin_dir / "skills").mkdir(parents=True)
    write_json(
        plugin_dir / "plugin.json",
        {
            "$schema": SCHEMA_ID,
            "name": name,
            "version": INITIAL_VERSION,
            "description": description.strip(),
            "author": dict(OWNER),
            "homepage": f"{SITE_URL}skills/{name}/",
            "repository": REPO_URL,
            "license": "MIT",
            "keywords": [name.removeprefix("emad-")],
        },
    )
    key = f"plugins/{name}"
    packages = config.setdefault("packages", {})
    packages[key] = {"component": name, "extra-files": [dict(VERSION_UPDATER)]}
    config["packages"] = dict(sorted(packages.items()))
    versions[key] = INITIAL_VERSION
    write_json(config_path, config)
    write_json(versions_path, dict(sorted(versions.items())))
    write_catalogs(root)
    return plugin_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a new plugin.")
    parser.add_argument("name", help="plugin name, for example emad-jobs")
    parser.add_argument("--description", required=True, help="one line: what the plugin covers")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        create_plugin(args.root, args.name, args.description)
    except ScaffoldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created plugins/{args.name}")
    print(f"next: add `{args.name}` to the plugin table in README.md")
    print(f"next: just new-skill {args.name} <skill-name>")
    return 0


if __name__ == "__main__":
    sys.exit(main())

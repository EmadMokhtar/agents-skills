"""Write the two catalog files from the plugin.json files.

Run: just sync          write the catalogs
     just catalogs      only check them (CI does this)

Each plugin.json is the single source of truth. The catalogs are generated,
so never edit them by hand:
- .claude-plugin/marketplace.json is read by Claude Code, GitHub Copilot,
  VS Code and `npx skills`;
- .agents/plugins/marketplace.json is the path the Codex docs name.
Catalogs never carry a version, so they cannot disagree with plugin.json.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from repo_model import (
    MARKETPLACE_NAME,
    OWNER,
    REPO_ROOT,
    Plugin,
    load_plugins,
    render_json,
)

CLAUDE_CATALOG = Path(".claude-plugin/marketplace.json")
CODEX_CATALOG = Path(".agents/plugins/marketplace.json")
DESCRIPTION = "Emad Mokhtar's agent skills, one plugin per category."
# Fields copied from plugin.json into each Claude Code catalog entry.
CLAUDE_ENTRY_FIELDS = ("description", "author", "homepage", "repository", "license", "keywords")


def claude_catalog(plugins: list[Plugin]) -> dict:
    return {
        "name": MARKETPLACE_NAME,
        "description": DESCRIPTION,
        "owner": dict(OWNER),
        "plugins": [
            {
                "name": p.name,
                "source": f"./plugins/{p.name}",
                **{k: p.manifest[k] for k in CLAUDE_ENTRY_FIELDS if k in p.manifest},
            }
            for p in plugins
        ],
    }


def codex_category(plugin_name: str) -> str:
    return plugin_name.removeprefix("emad-").replace("-", " ").title()


def codex_catalog(plugins: list[Plugin]) -> dict:
    return {
        "name": MARKETPLACE_NAME,
        "interface": {"displayName": "Emad's skills"},
        "plugins": [
            {
                "name": p.name,
                "source": {"source": "local", "path": f"./plugins/{p.name}"},
                # The Codex docs ask for both fields on every entry.
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": codex_category(p.name),
            }
            for p in plugins
        ],
    }


def expected_catalogs(root: Path) -> dict[Path, str]:
    plugins = load_plugins(root)
    return {
        root / CLAUDE_CATALOG: render_json(claude_catalog(plugins)),
        root / CODEX_CATALOG: render_json(codex_catalog(plugins)),
    }


def _current(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def stale_catalogs(root: Path) -> list[Path]:
    return [path for path, text in expected_catalogs(root).items() if _current(path) != text]


def write_catalogs(root: Path) -> list[Path]:
    written = []
    for path, text in expected_catalogs(root).items():
        if _current(path) != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report stale catalogs")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root
    if not args.check:
        for path in write_catalogs(root):
            print(f"wrote {path.relative_to(root).as_posix()}")
        return 0
    expected = expected_catalogs(root)
    stale = stale_catalogs(root)
    for path in stale:
        rel = path.relative_to(root).as_posix()
        sys.stdout.writelines(
            difflib.unified_diff(
                (_current(path) or "").splitlines(keepends=True),
                expected[path].splitlines(keepends=True),
                fromfile=f"{rel} (committed)",
                tofile=f"{rel} (expected)",
            )
        )
    if stale:
        print("The catalogs are out of date. Run: just sync", file=sys.stderr)
        return 1
    print("catalogs: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

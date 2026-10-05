"""Create a new skill inside an existing plugin.

Run: just new-skill <plugin> <skill-name>

It writes SKILL.md, README.md and one placeholder eval case. The description
starts with "TODO" on purpose: `just layout` fails until it is replaced.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from new_plugin import ScaffoldError
from repo_model import REPO_ROOT, SKILL_NAME_MAX, SKILL_NAME_RE, plugin_dirs

SKILL_BODY = """\
# {title}

## When to use

Describe the situations where an agent should load this skill.

## Steps

1. First step.

## Examples

Show one input and the output this skill should produce.
"""

README = """\
# {name}

What this skill does, when it triggers, and one before/after example.
This page is for people. The agent reads SKILL.md.
Use absolute links only: this file is also shown on the documentation site.
"""

EVALS = """\
# skill-lens eval cases for {name}. Each case needs `name` and `task`.
# Assertion kinds: contains, not_contains, regex, equals, file-produced, json-schema.
# Run for real with: just eval {plugin}/{name}
cases:
  - name: replace me with a real case
    task: Replace this with a realistic request that should trigger {name}.
    assertions:
      - kind: contains
        value: replace-me
"""


def create_skill(root: Path, plugin: str, name: str) -> Path:
    if not SKILL_NAME_RE.match(name):
        raise ScaffoldError(f"skill name {name!r} must match {SKILL_NAME_RE.pattern}")
    if len(name) > SKILL_NAME_MAX:
        raise ScaffoldError(f"skill name must be at most {SKILL_NAME_MAX} characters")
    plugin_dir = root / "plugins" / plugin
    if not (plugin_dir / "plugin.json").is_file():
        raise ScaffoldError(f"plugin {plugin!r} does not exist; create it with `just new-plugin`")
    for other in plugin_dirs(root):
        if (other / "skills" / name).exists():
            raise ScaffoldError(
                f"skill {name!r} already exists in plugin {other.name!r}; "
                "skill names must be unique across all plugins"
            )

    skill_dir = plugin_dir / "skills" / name
    (skill_dir / "evals").mkdir(parents=True)
    # yaml.safe_dump quotes any value that contains ": ", and writes lists in
    # block style, so the result is also valid strict YAML for `agentskills`.
    # A large width keeps each value on one line instead of wrapping at 80.
    frontmatter = yaml.safe_dump(
        {
            "name": name,
            "description": "TODO: say what this skill does and when an agent should use it.",
            "license": "MIT",
        },
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    title = name.replace("-", " ").capitalize()
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}---\n\n" + SKILL_BODY.format(title=title), encoding="utf-8"
    )
    (skill_dir / "README.md").write_text(README.format(name=name), encoding="utf-8")
    (skill_dir / "evals" / f"{name}.eval.yaml").write_text(
        EVALS.format(name=name, plugin=plugin), encoding="utf-8"
    )
    return skill_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a new skill inside a plugin.")
    parser.add_argument("plugin", help="existing plugin, for example emad-coding")
    parser.add_argument("name", help="skill name, for example conventional-commits")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        skill_dir = create_skill(args.root, args.plugin, args.name)
    except ScaffoldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {skill_dir.relative_to(args.root).as_posix()}")
    print("next: write the description and body in SKILL.md, README.md, and real eval cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())

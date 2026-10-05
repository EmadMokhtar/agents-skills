"""Turn the plugins and skills into documentation pages.

gen_skill_pages.py calls build_pages() while MkDocs builds the site. This
module never writes files, so the tests can call it directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from repo_model import (
    GITHUB_REPO,
    MARKETPLACE_NAME,
    REPO_ROOT,
    REPO_URL,
    Plugin,
    Skill,
    load_plugins,
    load_skills,
)


@dataclass(frozen=True)
class Page:
    path: str  # relative to docs/
    content: str
    mode: str = "w"  # "a" appends to a hand-written page
    edit_path: str | None = None  # relative to docs/, so "../plugins/..." for skill files


def fence_for(text: str) -> str:
    """A code fence longer than any run of backticks inside the text."""
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def indent(text: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "".join(pad + line if line.strip() else line for line in text.splitlines(True))


def one_line(text: object) -> str:
    """Make text safe for a single line or one Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def strip_title(markdown: str) -> str:
    """Drop a leading '# Title' line: the generated page already has a title."""
    lines = markdown.removeprefix("\ufeff").splitlines(True)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("# "):
        return "".join(lines[i + 1 :]).lstrip("\n")
    return "".join(lines)


def install_tabs(plugin: str, skill: str | None = None) -> str:
    npx = f"npx skills add {GITHUB_REPO}" + (f" --skill {skill}" if skill else "")
    claude_note = (
        f"    Then run `/{plugin}:{skill}`, or let Claude load it when a task needs it.\n\n"
        if skill
        else ""
    )
    return (
        '=== "Claude Code"\n\n'
        "    ```text\n"
        f"    /plugin marketplace add {GITHUB_REPO}\n"
        f"    /plugin install {plugin}@{MARKETPLACE_NAME}\n"
        "    ```\n\n"
        f"{claude_note}"
        '=== "Copilot CLI"\n\n'
        "    ```bash\n"
        f"    copilot plugin install {GITHUB_REPO}:plugins/{plugin}\n"
        "    ```\n\n"
        '=== "Codex"\n\n'
        "    ```bash\n"
        f"    codex plugin marketplace add {GITHUB_REPO}\n"
        "    ```\n\n"
        f"    Then open `/plugins` in Codex and install `{plugin}`.\n\n"
        '=== "Any tool (npx skills)"\n\n'
        "    ```bash\n"
        f"    {npx}\n"
        "    ```\n\n"
        "    Add `-a <tool>` to choose the tool, for example `-a cursor`.\n"
    )


def skill_page(skill: Skill) -> str:
    fm = skill.frontmatter
    source = f"{REPO_URL}/tree/main/plugins/{skill.plugin}/skills/{skill.name}"
    parts = [
        f"# {skill.name}\n\n",
        f"{one_line(fm.get('description', ''))}\n\n",
        f"**Plugin:** [`{skill.plugin}`](index.md) · [Source on GitHub]({source})\n\n",
    ]
    if skill.readme:
        parts.append(strip_title(skill.readme).rstrip("\n") + "\n\n")
    requirements = [
        (label, fm[key])
        for key, label in (
            ("compatibility", "Compatibility"),
            ("allowed-tools", "Pre-approved tools"),
        )
        if fm.get(key)
    ]
    if requirements:
        parts.append("## Requirements\n\n")
        parts += [f"- **{label}:** {one_line(value)}\n" for label, value in requirements]
        parts.append("\n")
    parts += ["## Install\n\n", install_tabs(skill.plugin, skill.name), "\n"]
    fence = fence_for(skill.text)
    parts += [
        '??? note "What the agent reads (SKILL.md)"\n\n',
        f"    {fence}markdown\n",
        indent(skill.text.rstrip("\n") + "\n"),
        f"    {fence}\n",
    ]
    return "".join(parts)


def plugin_page(plugin: Plugin, skills: list[Skill]) -> str:
    manifest = plugin.manifest
    version = manifest.get("version")
    shown = "not released yet" if version in (None, "0.0.0") else version
    rows = "".join(
        f"| [`{s.name}`]({s.name}.md) | {one_line(s.frontmatter.get('description', ''))} |\n"
        for s in skills
    )
    return (
        f"# {plugin.name}\n\n"
        f"{one_line(manifest.get('description', ''))}\n\n"
        f"**Version:** {shown} · "
        f"[Source on GitHub]({REPO_URL}/tree/main/plugins/{plugin.name})\n\n"
        "## Skills\n\n| Skill | What it does |\n| --- | --- |\n"
        f"{rows}\n"
        "## Install\n\n" + install_tabs(plugin.name)
    )


def catalog_table(plugins: list[Plugin], skills: list[Skill], base: str = "") -> str:
    rows = [
        f"| [`{p.name}`]({base}{p.name}/index.md) "
        f"| [`{s.name}`]({base}{p.name}/{s.name}.md) "
        f"| {one_line(s.frontmatter.get('description', ''))} |"
        for p in plugins
        for s in skills
        if s.plugin == p.name
    ]
    if not rows:
        return "_No skills yet._\n"
    return "\n".join(["| Plugin | Skill | What it does |", "| --- | --- | --- |", *rows]) + "\n"


def summary(plugins: list[Plugin], skills: list[Skill]) -> str:
    """The Skills navigation, in mkdocs-literate-nav's nested-list format."""
    lines = ["* [Catalog](index.md)"]
    for p in plugins:
        lines += [f"* {p.name}", f"    * [Overview]({p.name}/index.md)"]
        lines += [f"    * [{s.name}]({p.name}/{s.name}.md)" for s in skills if s.plugin == p.name]
    return "\n".join(lines) + "\n"


def build_pages(root: Path = REPO_ROOT) -> list[Page]:
    plugins = load_plugins(root)
    skills = load_skills(root)
    pages = [
        Page(
            "skills/index.md",
            "# Skills catalog\n\n"
            "Every skill in this repository, grouped by plugin. Install a whole plugin, "
            "or one skill with `npx skills`.\n\n" + catalog_table(plugins, skills),
        ),
        Page("skills/SUMMARY.md", summary(plugins, skills)),
        Page(
            "index.md",
            "\n## Catalog\n\n" + catalog_table(plugins, skills, "skills/"),
            "a",
        ),
    ]
    for plugin in plugins:
        own = [s for s in skills if s.plugin == plugin.name]
        pages.append(
            Page(
                f"skills/{plugin.name}/index.md",
                plugin_page(plugin, own),
                edit_path=f"../plugins/{plugin.name}/plugin.json",
            )
        )
        for skill in own:
            source = "README.md" if skill.readme is not None else "SKILL.md"
            pages.append(
                Page(
                    f"skills/{plugin.name}/{skill.name}.md",
                    skill_page(skill),
                    edit_path=f"../plugins/{plugin.name}/skills/{skill.name}/{source}",
                )
            )
    return pages

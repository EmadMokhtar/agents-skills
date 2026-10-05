from repo_model import load_plugins, load_skills
from skill_pages import (
    build_pages,
    catalog_table,
    fence_for,
    indent,
    install_tabs,
    one_line,
    plugin_page,
    skill_page,
    strip_title,
    summary,
)


def test_fence_is_longer_than_any_backtick_run():
    assert fence_for("plain") == "```"
    assert fence_for("has ``` inside") == "````"
    assert fence_for("has ````` inside") == "``````"


def test_indent_skips_blank_lines():
    assert indent("a\n\nb\n") == "    a\n\n    b\n"


def test_one_line_escapes_pipes_and_newlines():
    assert one_line("a | b\n  c") == "a \\| b c"


def test_strip_title_drops_only_a_leading_h1():
    assert strip_title("\n# name\n\nText\n") == "Text\n"
    assert strip_title("## Section\nText\n") == "## Section\nText\n"


def test_install_tabs_name_the_plugin_and_skill():
    tabs = install_tabs("emad-coding", "conventional-commits")
    assert "/plugin install emad-coding@emad-skills" in tabs
    assert "copilot plugin install EmadMokhtar/agents-skills:plugins/emad-coding" in tabs
    assert "codex plugin marketplace add EmadMokhtar/agents-skills" in tabs
    assert "npx skills add EmadMokhtar/agents-skills --skill conventional-commits" in tabs
    assert "`/emad-coding:conventional-commits`" in tabs
    assert "--skill" not in install_tabs("emad-coding")


def make(repo, body="Use it.\n", readme=None, extra=None):
    repo.add_plugin("emad-coding")
    fm = {"name": "demo", "description": "Does a | thing.", "license": "MIT", **(extra or {})}
    repo.add_skill("emad-coding", "demo", frontmatter=fm, body=body, readme=readme)
    return load_plugins(repo.root)[0], load_skills(repo.root)[0]


def test_skill_page_shows_readme_install_and_the_raw_skill_file(repo):
    _, skill = make(repo, readme="# demo\n\n## When it triggers\n\nAlways.\n")
    page = skill_page(skill)
    assert page.startswith("# demo\n\nDoes a \\| thing.\n")
    assert "## When it triggers" in page
    assert "# demo\n\n## When it triggers" not in page  # the README title is dropped
    assert "## Install" in page
    assert '??? note "What the agent reads (SKILL.md)"' in page
    assert "    ```markdown\n    ---\n    name: demo\n" in page
    assert "## Requirements" not in page


def test_skill_page_wraps_skill_md_in_a_longer_fence(repo):
    _, skill = make(repo, body="```bash\necho hi\n```\n")
    page = skill_page(skill)
    assert "    ````markdown\n" in page
    assert page.rstrip().endswith("````")


def test_skill_page_lists_requirements_when_present(repo):
    _, skill = make(repo, extra={"compatibility": "Needs git.", "allowed-tools": "Bash(git:*)"})
    page = skill_page(skill)
    assert "- **Compatibility:** Needs git." in page
    assert "- **Pre-approved tools:** Bash(git:*)" in page


def test_plugin_page_lists_skills_and_unreleased_version(repo):
    plugin, skill = make(repo)
    page = plugin_page(plugin, [skill])
    assert page.startswith("# emad-coding\n")
    assert "| [`demo`](demo.md) | Does a \\| thing. |" in page
    assert "**Version:** not released yet" in page


def test_catalog_table_uses_the_base_path(repo):
    plugin, skill = make(repo)
    table = catalog_table([plugin], [skill], base="skills/")
    assert "[`emad-coding`](skills/emad-coding/index.md)" in table
    assert "[`demo`](skills/emad-coding/demo.md)" in table
    assert catalog_table([], []) == "_No skills yet._\n"


def test_summary_is_a_literate_nav(repo):
    plugin, skill = make(repo)
    assert summary([plugin], [skill]) == (
        "* [Catalog](index.md)\n"
        "* emad-coding\n"
        "    * [Overview](emad-coding/index.md)\n"
        "    * [demo](emad-coding/demo.md)\n"
    )


def test_build_pages_paths_modes_and_edit_links(repo):
    make(repo, readme="# demo\n\nHi.\n")
    pages = {p.path: p for p in build_pages(repo.root)}
    assert set(pages) == {
        "skills/index.md",
        "skills/SUMMARY.md",
        "index.md",
        "skills/emad-coding/index.md",
        "skills/emad-coding/demo.md",
    }
    assert pages["index.md"].mode == "a"
    assert pages["index.md"].content.startswith("\n## Catalog\n")
    assert pages["skills/emad-coding/index.md"].edit_path == "../plugins/emad-coding/plugin.json"
    assert (
        pages["skills/emad-coding/demo.md"].edit_path
        == "../plugins/emad-coding/skills/demo/README.md"
    )

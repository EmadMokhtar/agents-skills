import json

import pytest

from repo_model import (
    RepoError,
    SkillFileError,
    load_plugins,
    load_skills,
    parse_skill_md,
    plugin_dirs,
    read_manifest,
    render_json,
    skill_dirs,
)


def test_parse_splits_frontmatter_and_body():
    data, body = parse_skill_md("---\nname: demo\ndescription: Says hi.\n---\n# Demo\n")
    assert data == {"name": "demo", "description": "Says hi."}
    assert body == "# Demo\n"


def test_parse_handles_crlf_and_bom():
    data, body = parse_skill_md("\ufeff---\r\nname: demo\r\n---\r\nBody\r\n")
    assert data == {"name": "demo"}
    assert body == "Body\n"


def test_parse_handles_quoted_colons_and_folded_text():
    text = "---\nname: demo\ndescription: >-\n  Use when the user\n  asks.\nnote: 'a: b'\n---\n"
    data, _ = parse_skill_md(text)
    assert data["description"] == "Use when the user asks."
    assert data["note"] == "a: b"


def test_parse_accepts_a_file_that_ends_at_the_closing_line():
    data, body = parse_skill_md("---\nname: demo\n---")
    assert data == {"name": "demo"}
    assert body == ""


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("name: demo\n", "must start with"),
        ("---\nname: demo\n", "no '---' line that closes"),
        ("---\n- a\n- b\n---\n", "must be a YAML mapping"),
        ("---\nname: [unclosed\n---\n", "not valid YAML"),
    ],
)
def test_parse_rejects_bad_frontmatter(text, message):
    with pytest.raises(SkillFileError, match=message):
        parse_skill_md(text)


def test_plugins_are_sorted_and_carry_their_manifest(repo):
    repo.add_plugin("emad-zeta")
    repo.add_plugin("emad-alpha")
    plugins = load_plugins(repo.root)
    assert [p.name for p in plugins] == ["emad-alpha", "emad-zeta"]
    assert plugins[0].manifest["name"] == "emad-alpha"


def test_no_plugins_folder_means_no_plugins(tmp_path):
    assert load_plugins(tmp_path) == []
    assert load_skills(tmp_path) == []


def test_hidden_entries_are_ignored(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one")
    (repo.root / "plugins" / ".DS_Store").write_text("x")
    (repo.root / "plugins" / ".hidden").mkdir()
    (repo.root / "plugins" / "emad-alpha" / "skills" / ".DS_Store").write_text("x")
    (repo.root / "plugins" / "emad-alpha" / "skills" / ".cache").mkdir()
    assert [p.name for p in plugin_dirs(repo.root)] == ["emad-alpha"]
    assert [s.name for s in skill_dirs(repo.root / "plugins" / "emad-alpha")] == ["one"]


def test_a_plugin_without_a_skills_folder_has_no_skills(repo):
    plugin_dir = repo.add_plugin("emad-alpha")
    (plugin_dir / "skills").rmdir()
    assert skill_dirs(plugin_dir) == []


def test_missing_manifest_names_the_file(repo):
    (repo.root / "plugins" / "emad-alpha").mkdir()
    with pytest.raises(RepoError) as info:
        read_manifest(repo.root / "plugins" / "emad-alpha")
    assert info.value.path.name == "plugin.json"
    assert info.value.reason == "missing"


def test_invalid_manifest_json_is_reported(repo):
    plugin_dir = repo.add_plugin("emad-alpha")
    (plugin_dir / "plugin.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(RepoError, match="not valid JSON"):
        read_manifest(plugin_dir)


def test_skills_know_their_plugin_text_and_readme(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one", readme="# one\n\nHello.\n")
    repo.add_skill("emad-alpha", "two")
    skills = load_skills(repo.root)
    assert [(s.plugin, s.name) for s in skills] == [("emad-alpha", "one"), ("emad-alpha", "two")]
    assert skills[0].frontmatter["description"] == "Use when testing one."
    assert skills[0].text.startswith("---\n")
    assert skills[0].readme == "# one\n\nHello.\n"
    assert skills[1].readme is None


def test_a_broken_skill_file_raises_repo_error_with_its_path(repo):
    repo.add_plugin("emad-alpha")
    skill_dir = repo.add_skill("emad-alpha", "one")
    (skill_dir / "SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
    with pytest.raises(RepoError) as info:
        load_skills(repo.root)
    assert info.value.path == skill_dir / "SKILL.md"


def test_render_json_is_stable():
    assert render_json({"b": "é", "a": [1]}) == '{\n  "b": "é",\n  "a": [\n    1\n  ]\n}\n'
    assert json.loads(render_json({"x": 1})) == {"x": 1}

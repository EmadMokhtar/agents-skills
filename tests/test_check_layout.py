import json

import pytest

from check_layout import MAX_SKILL_LINES, find_problems
from repo_model import SCHEMA_ID, SCHEMA_PATH


def problems_mentioning(problems, text):
    return [p for p in problems if text in p]


@pytest.fixture
def valid(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one")
    return repo


def write_manifest(repo, name, manifest):
    path = repo.root / "plugins" / name / "plugin.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_stored_schema_is_the_agent_plugins_1_0_0_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$id"] == SCHEMA_ID
    assert schema["additionalProperties"] is False


def test_a_valid_repository_has_no_problems(valid):
    assert find_problems(valid.root) == []


def test_the_real_repository_has_no_problems():
    assert find_problems() == []


def test_name_must_equal_the_folder_name(valid):
    manifest = json.loads((valid.root / "plugins/emad-alpha/plugin.json").read_text())
    manifest["name"] = "emad-beta"
    write_manifest(valid, "emad-alpha", manifest)
    assert problems_mentioning(find_problems(valid.root), "must equal the folder name")


def test_folder_name_needs_the_emad_prefix(repo):
    repo.add_plugin("tools")
    repo.add_skill("tools", "one")
    assert problems_mentioning(find_problems(repo.root), "folder name 'tools' must match")


def test_missing_manifest_is_reported(repo):
    (repo.root / "plugins" / "emad-alpha" / "skills" / "one").mkdir(parents=True)
    assert "plugins/emad-alpha/plugin.json: missing" in find_problems(repo.root)


def test_schema_violations_are_reported(valid):
    manifest = json.loads((valid.root / "plugins/emad-alpha/plugin.json").read_text())
    manifest["skills"] = ["./skills/jobs/"]
    write_manifest(valid, "emad-alpha", manifest)
    assert problems_mentioning(find_problems(valid.root), "'skills' was unexpected")


@pytest.mark.parametrize("field", ["version", "description", "author"])
def test_repository_required_fields(valid, field):
    manifest = json.loads((valid.root / "plugins/emad-alpha/plugin.json").read_text())
    del manifest[field]
    write_manifest(valid, "emad-alpha", manifest)
    assert problems_mentioning(find_problems(valid.root), f"'{field}' is required")


def test_extensions_are_not_allowed(valid):
    manifest = json.loads((valid.root / "plugins/emad-alpha/plugin.json").read_text())
    manifest["extensions"] = {"com.example.client": {}}
    write_manifest(valid, "emad-alpha", manifest)
    assert problems_mentioning(find_problems(valid.root), "remove 'extensions'")


def test_author_email_is_not_allowed(valid):
    manifest = json.loads((valid.root / "plugins/emad-alpha/plugin.json").read_text())
    manifest["author"]["email"] = "someone@example.com"
    write_manifest(valid, "emad-alpha", manifest)
    assert problems_mentioning(find_problems(valid.root), "remove author.email")


def test_a_plugin_needs_at_least_one_skill(repo):
    repo.add_plugin("emad-alpha")
    assert problems_mentioning(find_problems(repo.root), "has no skills")


def test_skill_names_are_unique_across_plugins(repo):
    repo.add_plugin("emad-alpha")
    repo.add_plugin("emad-beta")
    repo.add_skill("emad-alpha", "shared")
    repo.add_skill("emad-beta", "shared")
    found = problems_mentioning(find_problems(repo.root), "already used by plugin 'emad-alpha'")
    assert found == [
        "plugins/emad-beta/skills/shared: skill name 'shared' is already used by plugin "
        "'emad-alpha'; skill names must be unique across all plugins"
    ]


def test_skill_needs_mit_license(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one", frontmatter={"name": "one", "description": "Hi."})
    assert problems_mentioning(find_problems(repo.root), "license: MIT")


def test_scaffold_placeholder_description_is_reported(repo):
    repo.add_plugin("emad-alpha")
    fm = {"name": "one", "description": "TODO: say what it does.", "license": "MIT"}
    repo.add_skill("emad-alpha", "one", frontmatter=fm)
    assert problems_mentioning(find_problems(repo.root), "scaffold placeholder")


def test_long_skill_file_is_reported(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one", body="line\n" * MAX_SKILL_LINES)
    assert problems_mentioning(find_problems(repo.root), "keep SKILL.md under 500 lines")


def test_broken_skill_file_is_reported_not_raised(repo):
    repo.add_plugin("emad-alpha")
    skill_dir = repo.add_skill("emad-alpha", "one")
    (skill_dir / "SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
    assert problems_mentioning(find_problems(repo.root), "must start with a '---' line")


def test_skill_folder_without_skill_file_is_reported(valid):
    (valid.root / "plugins/emad-alpha/skills/empty").mkdir()
    assert "plugins/emad-alpha/skills/empty/SKILL.md: missing" in find_problems(valid.root)


@pytest.mark.parametrize(
    "rel",
    [
        "plugins/emad-alpha/skills/one/nested/SKILL.md",
        "plugins/emad-alpha/SKILL.md",
        "docs/SKILL.md",
        "SKILL.md",
    ],
)
def test_skill_files_in_the_wrong_place_are_reported(valid, rel):
    path = valid.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: x\n---\n", encoding="utf-8")
    assert f"{rel}: SKILL.md must sit at plugins/<plugin>/skills/<skill>/SKILL.md" in (
        find_problems(valid.root)
    )


@pytest.mark.parametrize("rel", ["tests/fixtures/x/SKILL.md", ".claude/worktrees/a/SKILL.md"])
def test_skill_files_in_tests_and_hidden_folders_are_ignored(valid, rel):
    path = valid.root / rel
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: x\n---\n", encoding="utf-8")
    assert find_problems(valid.root) == []


def test_dotfiles_are_not_problems(valid):
    (valid.root / "plugins" / ".DS_Store").write_text("x")
    (valid.root / "plugins" / "emad-alpha" / "skills" / ".DS_Store").write_text("x")
    assert find_problems(valid.root) == []

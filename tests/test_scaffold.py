import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from check_layout import find_problems
from new_plugin import ScaffoldError, create_plugin
from new_skill import create_skill
from repo_model import SCHEMA_PATH, read_skill

BIN = Path(sys.executable).parent


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_create_plugin_writes_a_valid_manifest_and_registers_it(repo):
    plugin_dir = create_plugin(repo.root, "emad-coding", "Coding workflow skills.")
    manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(manifest)) == []
    assert manifest["version"] == "0.0.0"
    assert manifest["homepage"] == "https://emadmokhtar.github.io/agents-skills/skills/emad-coding/"
    assert manifest["keywords"] == ["coding"]
    config = json.loads((repo.root / "release-please-config.json").read_text())
    assert config["packages"]["plugins/emad-coding"] == {
        "component": "emad-coding",
        "extra-files": [{"type": "json", "path": "plugin.json", "jsonpath": "$.version"}],
    }
    versions = json.loads((repo.root / ".release-please-manifest.json").read_text())
    assert versions == {"plugins/emad-coding": "0.0.0"}
    claude = json.loads((repo.root / ".claude-plugin/marketplace.json").read_text())
    assert [p["name"] for p in claude["plugins"]] == ["emad-coding"]


@pytest.mark.parametrize(
    ("name", "description", "message"),
    [
        ("coding", "Skills.", "must match"),
        ("emad-Coding", "Skills.", "must match"),
        ("emad-coding", "   ", "description must not be empty"),
    ],
)
def test_refused_plugin_writes_nothing(repo, name, description, message):
    before = snapshot(repo.root)
    with pytest.raises(ScaffoldError, match=message):
        create_plugin(repo.root, name, description)
    assert snapshot(repo.root) == before


def test_existing_plugin_is_refused_and_untouched(repo):
    repo.add_plugin("emad-coding")
    before = snapshot(repo.root)
    with pytest.raises(ScaffoldError, match="already exists"):
        create_plugin(repo.root, "emad-coding", "Again.")
    assert snapshot(repo.root) == before


def test_create_skill_writes_skill_readme_and_evals(repo):
    create_plugin(repo.root, "emad-coding", "Coding workflow skills.")
    skill_dir = create_skill(repo.root, "emad-coding", "commit-helper")
    skill = read_skill(skill_dir, "emad-coding")
    assert skill.frontmatter["name"] == "commit-helper"
    assert skill.frontmatter["license"] == "MIT"
    assert skill.frontmatter["description"].startswith("TODO")
    assert (skill_dir / "README.md").is_file()
    assert (skill_dir / "evals" / "commit-helper.eval.yaml").is_file()


def test_scaffolded_skill_passes_agentskills_and_skill_lens(repo):
    create_plugin(repo.root, "emad-coding", "Coding workflow skills.")
    skill_dir = create_skill(repo.root, "emad-coding", "commit-helper")
    # The scaffold description contains ": ", which strict YAML rejects unless quoted.
    validated = subprocess.run(
        [str(BIN / "agentskills"), "validate", str(skill_dir)], capture_output=True, text=True
    )
    assert validated.returncode == 0, validated.stdout + validated.stderr
    listed = subprocess.run(
        [str(BIN / "skill-lens"), "list", str(skill_dir)], capture_output=True, text=True
    )
    assert listed.returncode == 0, listed.stdout + listed.stderr
    assert "1 case(s)" in listed.stdout


def test_a_finished_scaffold_passes_the_layout_rules(repo):
    create_plugin(repo.root, "emad-coding", "Coding workflow skills.")
    skill_dir = create_skill(repo.root, "emad-coding", "commit-helper")
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    text = text.replace(
        "'TODO: say what this skill does and when an agent should use it.'",
        "Helps write commits. Use when committing.",
    )
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    # The author adds the README line, as `just new-plugin` reminds them to.
    with (repo.root / "README.md").open("a", encoding="utf-8") as f:
        f.write("- `emad-coding`\n")
    assert find_problems(repo.root) == []


@pytest.mark.parametrize(
    ("plugin", "name", "message"),
    [
        ("emad-coding", "Commit-Helper", "must match"),
        ("emad-coding", "commit--helper", "must match"),
        ("emad-coding", "a" * 65, "at most 64"),
        ("emad-missing", "commit-helper", "does not exist"),
        ("emad-coding", "shared", "already exists in plugin 'emad-other'"),
    ],
)
def test_refused_skill_writes_nothing(repo, plugin, name, message):
    create_plugin(repo.root, "emad-coding", "Coding workflow skills.")
    repo.add_plugin("emad-other")
    repo.add_skill("emad-other", "shared")
    before = snapshot(repo.root)
    with pytest.raises(ScaffoldError, match=message):
        create_skill(repo.root, plugin, name)
    assert snapshot(repo.root) == before

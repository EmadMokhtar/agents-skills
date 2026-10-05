import json

import pytest

from changed_skills import all_skills, main, skills_from_changed_files, skills_from_target


@pytest.fixture
def two(repo):
    repo.add_plugin("emad-alpha")
    repo.add_skill("emad-alpha", "one")
    repo.add_skill("emad-alpha", "two")
    return repo


def test_all_skills(two):
    assert all_skills(two.root) == [
        "plugins/emad-alpha/skills/one",
        "plugins/emad-alpha/skills/two",
    ]


def test_target_all_and_one(two):
    assert skills_from_target(two.root, "all") == all_skills(two.root)
    assert skills_from_target(two.root, "emad-alpha/two") == ["plugins/emad-alpha/skills/two"]


@pytest.mark.parametrize("target", ["emad-alpha", "emad-alpha/missing", "nope/one", ""])
def test_bad_targets_are_refused(two, target):
    with pytest.raises(ValueError, match="use <plugin>/<skill> or 'all'"):
        skills_from_target(two.root, target)


def test_changed_files_map_to_their_skill(two):
    files = [
        "plugins/emad-alpha/skills/one/SKILL.md",
        "plugins/emad-alpha/skills/one/evals/one.eval.yaml",
        "plugins/emad-alpha/plugin.json",
        "plugins/emad-alpha/skills/deleted/SKILL.md",
        "docs/index.md",
    ]
    assert skills_from_changed_files(two.root, files) == ["plugins/emad-alpha/skills/one"]


def test_main_prints_json(two, capsys):
    assert main(["--root", str(two.root), "--target", "all"]) == 0
    assert json.loads(capsys.readouterr().out) == all_skills(two.root)


def test_main_reports_a_bad_target(two, capsys):
    assert main(["--root", str(two.root), "--target", "x"]) == 2
    assert "use <plugin>/<skill>" in capsys.readouterr().err

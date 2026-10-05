import re

import pytest
import yaml

from repo_model import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$", re.MULTILINE)
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def test_there_are_workflows():
    assert WORKFLOWS


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_by_commit_sha(path):
    for ref, rest in USES.findall(path.read_text(encoding="utf-8")):
        if ref.startswith("./"):
            continue
        assert PINNED.match(ref), f"{path.name}: {ref} must be pinned to a full commit SHA"
        assert re.search(r"#\s*v\d", rest), f"{path.name}: {ref} needs a '# vX.Y.Z' comment"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_level_permissions_are_empty(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data.get("permissions") == {}, f"{path.name}: set 'permissions: {{}}' at the top"

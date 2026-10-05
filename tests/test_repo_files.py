from repo_model import REPO_ROOT


def test_claude_md_only_imports_agents_md():
    assert (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8") == "@AGENTS.md\n"


def test_path_scoped_copilot_instructions_declare_apply_to():
    for path in (REPO_ROOT / ".github" / "instructions").glob("*.instructions.md"):
        assert path.read_text(encoding="utf-8").startswith("---\napplyTo: "), path.name

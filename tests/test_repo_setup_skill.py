"""Tests for the repo-setup skill: its two scripts, and every module combination it renders.

The templates are held to the same rules as this repository's own workflows: every action is
pinned by commit SHA and every workflow starts with `permissions: {}`.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from repo_model import REPO_ROOT

SKILL = REPO_ROOT / "plugins" / "emad-coding" / "skills" / "repo-setup"
BIN = Path(sys.executable).parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scaffold = load("scaffold")
pin_actions = load("pin_actions")

VALUES = [
    "NAME=Tidal Tool",
    "SLUG=tidal-tool",
    "DESCRIPTION=A tool: it watches tides.",
    "OWNER=EmadMokhtar",
    "AUTHOR=Emad Mokhtar",
]
COMBINATIONS = {
    "base": [],
    "release": ["release"],
    "agents": ["agents"],
    "adr": ["adr"],
    "docs-site": ["docs-site"],
    "docs-site-adr": ["docs-site", "adr"],
    "docs-gates": ["docs-site", "docs-gates"],
    "nightly": ["nightly"],
    "security": ["security"],
    "container": ["security", "release", "container"],
    "everything": [
        "release",
        "agents",
        "adr",
        "docs-site",
        "docs-gates",
        "nightly",
        "security",
        "container",
    ],
    "unlicensed-base": [],
    "unlicensed-everything": [
        "release",
        "agents",
        "adr",
        "docs-site",
        "docs-gates",
        "nightly",
        "security",
        "container",
    ],
}


def run_scaffold(target: Path, modules: list[str], *extra: str) -> int:
    args = [str(target), "--modules", ",".join(modules)]
    for pair in VALUES:
        args += ["--set", pair]
    return scaffold.main([*args, *extra])


# --- pin_actions -------------------------------------------------------------------------


def test_parse_uses_matches_remote_actions_only():
    assert pin_actions.parse_uses("      - uses: actions/checkout@v7\n")
    assert pin_actions.parse_uses("        uses: github/codeql-action/init@v3  # v3.1.0")
    assert pin_actions.parse_uses("      - uses: ./.github/workflows/x.yml") is None
    assert pin_actions.parse_uses("      - uses: docker://alpine:3") is None
    assert pin_actions.parse_uses("      - run: echo uses: a/b@v1") is None


def test_parse_tags_prefers_the_commit_behind_an_annotated_tag():
    output = "aaa\trefs/tags/v1.0.0\nbbb\trefs/tags/v1.0.0^{}\nccc\trefs/heads/main\n"
    assert pin_actions.parse_tags(output) == {"v1.0.0": "bbb"}


def test_latest_for_major_picks_the_newest_stable_release():
    tags = {"v4": "a", "v4.1.0": "b", "v4.2.0": "c", "v4.3.0-beta.1": "d", "v5.0.0": "e"}
    assert pin_actions.latest_for_major(tags, 4) == ("v4.2.0", "c")
    assert pin_actions.latest_for_major(tags, 6) is None


@pytest.mark.parametrize(
    ("ref", "comment", "expected"),
    [
        ("v7", None, 7),
        ("v7.0.1", None, 7),
        ("a" * 40, "  # v10.2.0", 10),
        ("a" * 40, None, None),
        ("main", None, None),
    ],
)
def test_hint_major(ref, comment, expected):
    assert pin_actions.hint_major(ref, comment) == expected


def test_pin_file_rewrites_then_leaves_a_current_pin_alone(tmp_path, monkeypatch):
    sha = "1" * 40
    monkeypatch.setattr(pin_actions, "fetch_tags", lambda repo: {"v7": "9" * 40, "v7.0.1": sha})
    workflow = tmp_path / "w.yml"
    workflow.write_text("steps:\n  - uses: actions/checkout@v7\n  - run: echo hi\n")
    cache: dict = {}

    first = pin_actions.pin_file(workflow, cache, check=False)
    assert len(first) == 1
    assert f"uses: actions/checkout@{sha}  # v7.0.1\n" in workflow.read_text()

    assert pin_actions.pin_file(workflow, cache, check=False) == []


def test_pin_file_in_check_mode_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(pin_actions, "fetch_tags", lambda repo: {"v7.0.1": "1" * 40})
    workflow = tmp_path / "w.yml"
    original = "steps:\n  - uses: actions/checkout@v7\n"
    workflow.write_text(original)
    assert pin_actions.pin_file(workflow, {}, check=True)
    assert workflow.read_text() == original


# --- scaffold: blocks, values, safety ----------------------------------------------------


def test_select_blocks_keeps_only_the_chosen_modules():
    text = (
        "a\n# @if docs-site\nb\n# @else\nc\n# @endif\n"
        "<!-- @if security -->\nd\n<!-- @endif -->\ne\n"
    )
    assert scaffold.select_blocks(text, {"docs-site"}, "t") == "a\nb\ne\n"
    assert scaffold.select_blocks(text, {"security"}, "t") == "a\nc\nd\ne\n"


def test_select_blocks_rejects_bad_markers():
    with pytest.raises(SystemExit, match="unknown module"):
        scaffold.select_blocks("# @if nope\n# @endif\n", set(), "t")
    with pytest.raises(SystemExit, match="without @endif"):
        scaffold.select_blocks("# @if docs-site\n", set(), "t")
    with pytest.raises(SystemExit, match="without @if"):
        scaffold.select_blocks("# @endif\n", set(), "t")


def test_build_values_adds_defaults_and_validates():
    values = scaffold.build_values(VALUES, "MIT")
    assert values["BRANCH"] == "main"
    assert values["SITE_URL"] == "https://emadmokhtar.github.io/tidal-tool/"
    assert values["OWNER_LOWER"] == "emadmokhtar"
    with pytest.raises(SystemExit, match="missing"):
        scaffold.build_values(["NAME=x"], "MIT")
    with pytest.raises(SystemExit, match="double quote"):
        scaffold.build_values([*VALUES, 'NAME=a"b'], "MIT")
    with pytest.raises(SystemExit, match="SLUG"):
        scaffold.build_values([*VALUES, "SLUG=a b"], "MIT")


def test_a_module_that_needs_another_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="needs 'docs-site'"):
        run_scaffold(tmp_path, ["docs-gates"])
    with pytest.raises(SystemExit, match="needs 'security'"):
        run_scaffold(tmp_path, ["container", "release"])
    with pytest.raises(SystemExit, match="needs 'release'"):
        run_scaffold(tmp_path, ["container", "security"])


def test_scaffold_never_overwrites_a_file(tmp_path):
    (tmp_path / "README.md").write_text("mine\n")
    (tmp_path / "LICENSE").write_text("my licence\n")
    run_scaffold(tmp_path, [])
    assert (tmp_path / "README.md").read_text() == "mine\n"
    assert (tmp_path / "LICENSE").read_text() == "my licence\n"
    assert (tmp_path / "justfile").is_file()


def test_scaffold_is_idempotent(tmp_path, capsys):
    run_scaffold(tmp_path, ["docs-site"])
    capsys.readouterr()
    run_scaffold(tmp_path, ["docs-site"])
    report = capsys.readouterr().out
    assert "created" not in report
    assert "differs" not in report


def test_gitignore_gets_only_the_missing_lines(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules/\n.venv/\n")
    run_scaffold(tmp_path, [])
    lines = (tmp_path / ".gitignore").read_text().splitlines()
    assert lines[:2] == ["node_modules/", ".venv/"]
    assert lines.count(".venv/") == 1
    assert ".env" in lines


def test_dry_run_writes_nothing(tmp_path):
    run_scaffold(tmp_path, ["docs-site"], "--dry-run")
    assert list(tmp_path.iterdir()) == []


def test_skip_leaves_matching_files_out(tmp_path):
    run_scaffold(tmp_path, [], "--skip", ".github/workflows/release.yml")
    assert not (tmp_path / ".github" / "workflows" / "release.yml").exists()
    assert (tmp_path / ".github" / "workflows" / "ci.yml").is_file()


def test_tmpl_suffix_is_stripped(tmp_path):
    run_scaffold(tmp_path, ["agents"])
    assert (tmp_path / "AGENTS.md").read_text().startswith("# Agent instructions")
    assert (tmp_path / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert not list(tmp_path.rglob("*.tmpl"))


def test_the_licence_is_chosen_and_filled_in(tmp_path):
    run_scaffold(tmp_path, [], "--license", "Apache-2.0")
    assert "Apache License" in (tmp_path / "LICENSE").read_text()


def test_licence_none_writes_no_licence_and_no_licence_text(tmp_path):
    run_scaffold(tmp_path, ["docs-site"], "--license", "none")
    assert not (tmp_path / "LICENSE").exists()
    for rel in ["README.md", "mkdocs.yml"]:
        body = (tmp_path / rel).read_text()
        assert "LICENSE" not in body, rel
        assert "icense" not in body.replace("Licensed", ""), rel


def test_several_source_prefixes_become_several_arguments(tmp_path):
    args = [
        str(tmp_path),
        "--modules",
        "docs-site,docs-gates",
        "--set",
        "SOURCE_PREFIX=cmd/,internal/",
    ]
    for pair in VALUES:
        args += ["--set", pair]
    scaffold.main(args)
    justfile = (tmp_path / "justfile").read_text()
    assert "--source 'cmd/' --source 'internal/'" in justfile
    assert "`cmd/` or `internal/`" in (tmp_path / "docs" / "contributing.md").read_text()


def test_the_report_lists_what_to_stage_and_pin(tmp_path, capsys):
    run_scaffold(tmp_path, ["release"])
    report = capsys.readouterr().out
    assert "git add -- " in report
    assert "pin_actions.py .github/workflows/ci.yml" in report
    capsys.readouterr()
    other = tmp_path / "native"
    other.mkdir()
    run_scaffold(other, ["release"], "--toolchain", "native")
    pin_line = next(
        line for line in capsys.readouterr().out.splitlines() if line.startswith("pin the new")
    )
    assert ".github/actions/setup-tools/action.yml" in pin_line


# --- every combination --------------------------------------------------------------------


CASES = [
    (f"{name}-{toolchain}", modules, toolchain)
    for name, modules in COMBINATIONS.items()
    for toolchain in ("uv", "native")
]


@pytest.fixture(params=CASES, ids=[case[0] for case in CASES])
def rendered(request, tmp_path) -> tuple[str, list[str], Path]:
    name, modules, toolchain = request.param
    extra = ["--toolchain", toolchain]
    if name.startswith("unlicensed"):
        extra += ["--license", "none"]
    run_scaffold(tmp_path, modules, *extra)
    return name, modules, tmp_path


def toolchain_of(name: str) -> str:
    return name.rsplit("-", 1)[1]


def text_files(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*")) if p.is_file()]


def test_nothing_unfilled_is_left(rendered):
    _, _, root = rendered
    for path in text_files(root):
        body = path.read_text(encoding="utf-8")
        if path.name.startswith("LICENSE"):
            continue
        assert not re.search(r"__[A-Z][A-Z0-9_]*__", body), f"{path}: placeholder left"
        assert not re.search(r"@(if|else|endif)\b", body), f"{path}: marker left"


def test_every_yaml_and_toml_file_parses(rendered):
    _, _, root = rendered
    for path in text_files(root):
        if path.suffix in {".yml", ".yaml"}:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.suffix == ".toml":
            tomllib.loads(path.read_text(encoding="utf-8"))


def test_workflows_follow_the_repository_policy(rendered):
    _, _, root = rendered
    uses = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$", re.MULTILINE)
    pinned = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    assert workflows
    for path in workflows:
        body = path.read_text(encoding="utf-8")
        assert yaml.safe_load(body).get("permissions") == {}, f"{path.name}: permissions"
        for ref, rest in uses.findall(body):
            if ref.startswith("./"):
                continue
            assert pinned.match(ref), f"{path.name}: {ref} is not pinned by SHA"
            assert re.search(r"#\s*v\d", rest), f"{path.name}: {ref} needs a version comment"


def test_the_expected_files_exist_for_the_modules(rendered):
    name, modules, root = rendered
    expected = {
        "release": [".github/workflows/release.yml"],
        "agents": ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"],
        "adr": ["docs/adr/template.md", "docs/adr/README.md"],
        "docs-site": ["mkdocs.yml", "docs/index.md", ".github/workflows/docs.yml"],
        "docs-gates": ["lychee.toml", "scripts/check_docs_updated.py"],
        "nightly": [".github/workflows/nightly.yml"],
        "security": [
            ".github/workflows/security.yml",
            "ops/trivy/.trivyignore.yaml",
            "SECURITY.md",
        ],
        "container": [".github/workflows/container.yml", ".github/workflows/publish-images.yml"],
    }
    for module, files in expected.items():
        for rel in files:
            assert (root / rel).exists() == (module in modules), f"{module}: {rel}"
    for rel in ["justfile", ".github/workflows/ci.yml", "docs/contributing.md"]:
        assert (root / rel).is_file()
    assert (root / "LICENSE").exists() == (not name.startswith("unlicensed"))

    uv_only = ["pyproject.toml", ".python-version", ".pre-commit-config.yaml"]
    native_only = [".githooks/commit-msg", ".githooks/pre-commit", ".editorconfig"]
    native_only += [".github/actions/setup-tools/action.yml"]
    toolchain = toolchain_of(name)
    for rel in uv_only:
        assert (root / rel).exists() == (toolchain == "uv"), rel
    for rel in native_only:
        assert (root / rel).exists() == (toolchain == "native"), rel
    # commitizen settings live in pyproject.toml with uv, and in its own .cz.toml without it
    assert (root / ".cz.toml").exists() == (toolchain == "native" and "release" in modules)
    # nothing needs Docker's compose any more: Trivy is a program like the others
    assert not (root / "ops" / "trivy" / "compose.yaml").exists()
    assert not (root / "ops" / "tools").exists()


def test_the_docs_nav_points_at_real_pages(rendered):
    _, modules, root = rendered
    if "docs-site" not in modules:
        return
    config = yaml.safe_load((root / "mkdocs.yml").read_text(encoding="utf-8"))
    pages: list[str] = []

    def walk(node):
        if isinstance(node, str):
            pages.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)

    walk(config["nav"])
    assert pages
    for page in pages:
        assert (root / "docs" / page).is_file(), page


def test_the_justfile_lists_and_check_depends_on_the_right_gates(rendered):
    _, modules, root = rendered
    just = shutil.which("just")
    if just is None:
        pytest.skip("just is not installed")
    listing = subprocess.run(
        [just, "--justfile", str(root / "justfile"), "--list"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "check" in listing
    assert ("docs-build" in listing) == ("docs-site" in modules)
    assert ("scan-tree" in listing) == ("security" in modules)
    assert ("build-image" in listing) == ("container" in modules)
    check_line = next(
        line for line in (root / "justfile").read_text().splitlines() if line.startswith("check:")
    )
    assert ("docs-build" in check_line) == ("docs-site" in modules)


def test_actionlint_accepts_the_workflows(rendered):
    _, _, root = rendered
    actionlint = BIN / "actionlint"
    if not actionlint.exists():
        pytest.skip("actionlint is not installed")
    # Pass the files, because without a .git folder actionlint cannot find the project root.
    files = sorted(str(p) for p in (root / ".github" / "workflows").glob("*.yml"))
    result = subprocess.run([str(actionlint), *files], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_shipped_scripts_compile(tmp_path):
    run_scaffold(tmp_path, ["docs-site", "docs-gates"])
    for path in (tmp_path / "scripts").glob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_nothing_points_at_a_module_that_was_not_chosen(rendered):
    _, modules, root = rendered
    bodies = {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in text_files(root)
        if p.suffix in {".md", ".yml", ".yaml", ".toml"} and p.name != "LICENSE"
    }
    if "adr" not in modules:
        for rel, body in bodies.items():
            assert "adr/" not in body, f"{rel} mentions adr/ but the adr module is not installed"
    if "release" not in modules:
        for rel, body in bodies.items():
            assert "RELEASE_TOKEN" not in body, f"{rel} mentions RELEASE_TOKEN without release"
            assert "bump:" not in body, f"{rel} mentions bump: without release"
        assert "version_provider" not in bodies.get("pyproject.toml", "")
        assert ".cz.toml" not in bodies
        assert "next-version" not in (root / "justfile").read_text()
    if "agents" not in modules:
        assert not any("AGENTS.md" in body for body in bodies.values()), "dangling AGENTS.md"


def test_every_file_passes_the_whitespace_hooks(rendered):
    """The files must already satisfy end-of-file-fixer and trailing-whitespace."""
    _, _, root = rendered
    for path in text_files(root):
        body = path.read_text(encoding="utf-8")
        assert body.endswith("\n") and not body.endswith("\n\n"), f"{path.name}: file ending"
        for number, line in enumerate(body.splitlines(), 1):
            assert line == line.rstrip(), f"{path.name}:{number}: trailing whitespace"


def test_a_native_toolchain_repo_has_no_uv_and_no_python_project(rendered):
    """A repository that is not Python must not need uv or a Python project to run its tools."""
    name, _, root = rendered
    if toolchain_of(name) != "native":
        return
    for banned in ["pyproject.toml", "uv.lock", ".python-version", ".pre-commit-config.yaml"]:
        assert not (root / banned).exists(), banned
    word = re.compile(r"\buvx?\b|setup-uv|pyproject\.toml|uv\.lock|\.python-version")
    for path in text_files(root):
        rel = path.relative_to(root).as_posix()
        if rel == "docs/adr/0005-run-tools-the-same-way-everywhere.md":
            continue  # the record names uv as the alternative it rejected
        body = path.read_text(encoding="utf-8")
        assert not word.search(body), f"{rel} mentions uv or a Python project file"


def test_the_hooks_are_executable_and_the_commit_message_check_works(tmp_path):
    run_scaffold(tmp_path, [], "--toolchain", "native")
    hook = tmp_path / ".githooks" / "commit-msg"
    assert hook.stat().st_mode & 0o111
    assert (tmp_path / ".githooks" / "pre-commit").stat().st_mode & 0o111

    def check(message: str) -> int:
        message_file = tmp_path / "MSG"
        message_file.write_text(message + "\n")
        return subprocess.run(
            ["sh", str(hook), str(message_file)], capture_output=True, check=False
        ).returncode

    assert check("feat: add a login endpoint") == 0
    assert check("fix(auth)!: reject expired tokens") == 0
    assert check("Merge branch 'main' into feature") == 0
    assert check("Update auth") != 0
    assert check("feat:missing space") != 0
    assert check("Feat: wrong case") != 0
    # the description follows the same rule as the pull request title check
    assert check("feat: Add login") != 0
    assert check("feat: add login.") != 0
    assert check("feat(api)!: remove v1 endpoints") == 0


def test_toolchain_auto_picks_uv_only_for_a_python_project(tmp_path):
    assert scaffold.detect_toolchain(tmp_path) == "native"
    (tmp_path / "go.mod").write_text("module example.com/x\n")
    assert scaffold.detect_toolchain(tmp_path) == "native"
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert scaffold.detect_toolchain(tmp_path) == "uv"


def test_a_file_in_a_switched_off_block_is_not_written(tmp_path):
    run_scaffold(tmp_path, [], "--toolchain", "native")
    # .cz.toml is wrapped in `@if release`, so without release it comes out empty and is skipped
    assert not (tmp_path / ".cz.toml").exists()


def test_the_setup_action_pins_every_tool_and_every_action(rendered):
    name, modules, root = rendered
    action = root / ".github" / "actions" / "setup-tools" / "action.yml"
    if toolchain_of(name) != "native":
        assert not action.exists()
        return
    body = action.read_text()
    config = yaml.safe_load(body)
    assert config["runs"]["using"] == "composite"
    inputs = set(config["inputs"])
    assert {"actionlint", "gitleaks", "editorconfig"} <= inputs
    assert ("commitizen" in inputs) == ("release" in modules)
    assert ("mkdocs" in inputs) == ("docs-site" in modules)
    assert ("trivy" in inputs) == ("security" in modules)
    # every tool is installed at an exact version, never "latest"
    assert re.search(r"actionlint@v\d+\.\d+\.\d+", body)
    assert re.search(r"gitleaks/v8@v\d+\.\d+\.\d+", body)
    assert re.search(r"editorconfig-checker@v\d+\.\d+\.\d+", body)
    if "release" in modules:
        assert re.search(r"commitizen==\d+\.\d+\.\d+", body)
    if "docs-site" in modules:
        assert re.search(r"mkdocs-material==\d+\.\d+\.\d+", body)
    # actions used inside the composite action follow the same SHA rule as workflows
    for ref in re.findall(r"^\s*(?:-\s*)?uses:\s*(\S+)", body, re.MULTILINE):
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref), ref


def test_every_workflow_uses_the_setup_action_instead_of_installing_tools_itself(rendered):
    name, modules, root = rendered
    if toolchain_of(name) != "native":
        return
    ci = (root / ".github" / "workflows" / "ci.yml").read_text()
    assert "uses: ./.github/actions/setup-tools" in ci
    assert "setup-uv" not in ci
    for path in (root / ".github" / "workflows").glob("*.yml"):
        assert "go install" not in path.read_text(), path.name


def test_doctor_lists_exactly_the_tools_of_the_chosen_modules(rendered):
    name, modules, root = rendered
    if toolchain_of(name) != "native":
        return
    justfile = (root / "justfile").read_text()
    doctor = justfile.split("doctor:")[1].split("\n\n")[0]
    for tool in ["actionlint", "gitleaks", "editorconfig-checker"]:
        assert f"check {tool} " in doctor
    assert ("check cz " in doctor) == ("release" in modules)
    assert ("check mkdocs " in doctor) == ("docs-site" in modules)
    assert ("check lychee " in doctor) == ("docs-gates" in modules)
    assert ("check trivy " in doctor) == ("security" in modules)
    assert ("check docker " in doctor) == ("container" in modules)
    assert "brew install" in doctor


def test_the_freshness_script_needs_only_the_standard_library(tmp_path):
    run_scaffold(tmp_path, ["docs-site", "docs-gates"])
    script = tmp_path / "scripts" / "check_docs_freshness.py"
    body = script.read_text()
    assert "import yaml" not in body
    spec = importlib.util.spec_from_file_location("freshness", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["freshness"] = module
    spec.loader.exec_module(module)
    meta = module.parse_frontmatter(
        '---\nlast_reviewed: 2026-10-11\ncovers:\n  - justfile\n  - "ops/"\n---\n# Page\n'
    )
    assert str(meta["last_reviewed"]) == "2026-10-11"
    assert meta["covers"] == ["justfile", "ops/"]
    assert module.parse_frontmatter("# no front matter\n") == {}
    assert "last_reviewed" not in module.parse_frontmatter("---\nlast_reviewed: soon\n---\nx")


def test_the_listing_counts_the_adr_records_correctly(capsys):
    scaffold.main(["--list"])
    listing = capsys.readouterr().out
    records = len(list((SKILL / "assets" / "adr" / "docs" / "adr").glob("0*.md")))
    assert records == 5
    assert "five starter records" in listing


def test_no_yaml_library_is_required_for_the_docs_scripts(tmp_path):
    run_scaffold(tmp_path, ["docs-site", "docs-gates"], "--toolchain", "uv")
    assert "yaml" not in (tmp_path / "pyproject.toml").read_text().lower()


# --- review findings: shell safety, symlinks, honest CI wording, release repair -------------


@pytest.mark.parametrize(
    "prefix",
    [
        "src/'; touch /tmp/pwned; '",
        "src/ && rm -rf /",
        "$(id)/",
        "`id`/",
        "a b/",
        'src/"x',
        "",
        ",",
    ],
)
def test_a_source_folder_with_shell_characters_is_refused(tmp_path, prefix):
    args = [str(tmp_path), "--modules", "docs-site,docs-gates", "--set", f"SOURCE_PREFIX={prefix}"]
    for pair in VALUES:
        args += ["--set", pair]
    with pytest.raises(SystemExit, match="SOURCE_PREFIX|double quote"):
        scaffold.main(args)
    assert list(tmp_path.iterdir()) == []


def test_normal_source_folders_still_work(tmp_path):
    run_scaffold(tmp_path, ["docs-site", "docs-gates"])
    justfile = (tmp_path / "justfile").read_text()
    assert "--source 'src/'" in justfile


def test_a_dangling_symlink_is_not_written_through(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").symlink_to(outside / "stolen.md")  # dangling: the target is missing
    with pytest.raises(SystemExit, match="symlink"):
        run_scaffold(repo, [])
    assert not (outside / "stolen.md").exists()
    assert not (repo / "justfile").exists()  # nothing was written before the refusal


def test_a_symlinked_parent_folder_is_not_written_through(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SystemExit, match="symlink"):
        run_scaffold(repo, [])
    assert list(outside.iterdir()) == []


def test_a_symlinked_gitignore_is_not_appended_to(tmp_path):
    target_file = tmp_path / "elsewhere.txt"
    target_file.write_text("keep\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").symlink_to(target_file)
    with pytest.raises(SystemExit, match="symlink"):
        run_scaffold(repo, [])
    assert target_file.read_text() == "keep\n"


def test_ci_only_gates_are_named_in_the_contributing_guide(rendered):
    _, modules, root = rendered
    guide = (root / "docs" / "contributing.md").read_text()
    justfile = (root / "justfile").read_text()
    extras = {"docs-gates": "docs-updated", "security": "scan-tree", "container": "scan-image"}
    chosen = [module for module in extras if module in modules]
    assert ("CI also runs gates that need GitHub or the network" in guide) == bool(chosen)
    assert ("CI also runs gates that need GitHub" in justfile) == bool(chosen)
    for module, recipe in extras.items():
        assert (f"`just {recipe}`" in guide or recipe in guide) == (module in modules), module


def release_workflow(root: Path) -> dict:
    return yaml.safe_load((root / ".github" / "workflows" / "release.yml").read_text())


def test_the_release_can_be_repaired_by_running_it_by_hand(tmp_path):
    run_scaffold(tmp_path, ["release", "security", "container"], "--toolchain", "native")
    workflow = release_workflow(tmp_path)
    assert "workflow_dispatch" in workflow[True]  # PyYAML reads the key `on` as True
    job = workflow["jobs"]["release"]
    assert set(job["outputs"]) == {"published", "version"}
    publish = next(step for step in job["steps"] if step.get("id") == "publish")
    assert "gh release view" in publish["run"]
    assert "git describe --tags" in publish["run"]
    assert workflow["jobs"]["publish-images"]["if"] == "needs.release.outputs.published == 'true'"
    images = yaml.safe_load((tmp_path / ".github" / "workflows" / "publish-images.yml").read_text())
    assert "workflow_dispatch" in images[True]
    assert images[True]["workflow_dispatch"]["inputs"]["version"]["required"] is True


@pytest.fixture
def release_repo(tmp_path):
    """A repository with a tag, a fake `gh`, and the publish step of release.yml."""
    run_scaffold(tmp_path, ["release"], "--toolchain", "native")
    step = next(
        step
        for step in release_workflow(tmp_path)["jobs"]["release"]["steps"]
        if step.get("id") == "publish"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$FAKE_GH_LOG"\n'
        'if [ "$1 $2" = "release view" ]; then [ "$FAKE_RELEASE_EXISTS" = "yes" ]; exit $?; fi\n'
        "exit 0\n"
    )
    gh.chmod(0o755)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t.t"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(
        [*git, "commit", "-q", "--allow-empty", "-m", "feat: first"], cwd=tmp_path, check=True
    )
    return tmp_path, step["run"], bin_dir


def run_publish(release_repo, *, bumped: str, version: str = "", exists: str = "no", tag: str = ""):
    root, script, bin_dir = release_repo
    if tag:
        subprocess.run(["git", "tag", tag], cwd=root, check=True)
    output = root / "output.txt"
    log = root / "gh.log"
    output.write_text("")
    log.write_text("")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CZ": "echo",
        "GITHUB_OUTPUT": str(output),
        "FAKE_GH_LOG": str(log),
        "FAKE_RELEASE_EXISTS": exists,
        "BUMPED": bumped,
        "BUMPED_VERSION": version,
        "GH_TOKEN": "x",
    }
    subprocess.run(["bash", "-e", "-c", script], cwd=root, env=env, check=True, capture_output=True)
    return output.read_text(), log.read_text()


def test_publish_creates_the_release_after_a_bump(release_repo):
    output, log = run_publish(release_repo, bumped="true", version="0.2.0")
    assert "published=true" in output and "version=0.2.0" in output
    assert "release create v0.2.0" in log


def test_publish_repairs_a_tag_that_has_no_release(release_repo):
    output, log = run_publish(release_repo, bumped="false", tag="v0.1.0")
    assert "published=true" in output and "version=0.1.0" in output
    assert "release create v0.1.0" in log


def test_publish_does_nothing_when_the_release_exists(release_repo):
    output, log = run_publish(release_repo, bumped="false", tag="v0.1.0", exists="yes")
    assert "published=false" in output
    assert "release create" not in log


def test_publish_does_nothing_before_the_first_tag(release_repo):
    output, log = run_publish(release_repo, bumped="false")
    assert "published=false" in output
    assert "release create" not in log

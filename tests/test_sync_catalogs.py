import json

from repo_model import CLAUDE_MANIFEST, SCHEMA_ID, load_plugins
from sync_catalogs import (
    CLAUDE_CATALOG,
    CODEX_CATALOG,
    claude_catalog,
    claude_manifest,
    codex_catalog,
    codex_category,
    main,
)


def test_claude_catalog_lists_plugins_without_versions(repo):
    repo.add_plugin("emad-zeta", keywords=["z"], homepage="https://example.com/z")
    repo.add_plugin("emad-alpha")
    catalog = claude_catalog(load_plugins(repo.root))
    assert catalog["name"] == "emad-skills"
    assert catalog["owner"] == {"name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar"}
    assert catalog["description"]
    assert [p["name"] for p in catalog["plugins"]] == ["emad-alpha", "emad-zeta"]
    zeta = catalog["plugins"][1]
    assert zeta["source"] == "./plugins/emad-zeta"
    assert zeta["keywords"] == ["z"]
    assert zeta["homepage"] == "https://example.com/z"
    assert all("version" not in p for p in catalog["plugins"])


def test_codex_catalog_uses_local_sources_and_policies(repo):
    repo.add_plugin("emad-job-search")
    catalog = codex_catalog(load_plugins(repo.root))
    assert catalog["name"] == "emad-skills"
    assert catalog["plugins"] == [
        {
            "name": "emad-job-search",
            "source": {"source": "local", "path": "./plugins/emad-job-search"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Job Search",
        }
    ]


def test_codex_category_comes_from_the_plugin_name():
    assert codex_category("emad-coding") == "Coding"


def test_empty_repository_gives_empty_plugin_lists(repo):
    assert claude_catalog([])["plugins"] == []
    assert codex_catalog([])["plugins"] == []


def test_sync_writes_then_check_passes(repo, capsys):
    repo.add_plugin("emad-alpha")
    assert main(["--root", str(repo.root)]) == 0
    written = json.loads((repo.root / CLAUDE_CATALOG).read_text(encoding="utf-8"))
    assert written["plugins"][0]["name"] == "emad-alpha"
    assert (repo.root / CODEX_CATALOG).is_file()
    assert main(["--root", str(repo.root), "--check"]) == 0


def test_check_reports_a_stale_catalog_and_writes_nothing(repo, capsys):
    plugin_dir = repo.add_plugin("emad-alpha")
    main(["--root", str(repo.root)])
    manifest = json.loads((plugin_dir / "plugin.json").read_text())
    manifest["description"] = "Changed."
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    before = (repo.root / CLAUDE_CATALOG).read_text(encoding="utf-8")
    assert main(["--root", str(repo.root), "--check"]) == 1
    out = capsys.readouterr()
    assert '+      "description": "Changed."' in out.out
    assert "just sync" in out.err
    assert (repo.root / CLAUDE_CATALOG).read_text(encoding="utf-8") == before


def test_claude_manifest_is_plugin_json_without_the_schema_field(repo):
    repo.add_plugin("emad-alpha", keywords=["a"])
    (plugin,) = load_plugins(repo.root)
    manifest = claude_manifest(plugin)
    assert "$schema" not in manifest
    assert manifest == {k: v for k, v in plugin.manifest.items() if k != "$schema"}
    # The key order stays the same as in plugin.json.
    assert list(manifest) == [k for k in plugin.manifest if k != "$schema"]


def test_sync_writes_the_claude_manifest_into_each_plugin(repo):
    alpha = repo.add_plugin("emad-alpha")
    beta = repo.add_plugin("emad-beta")
    assert main(["--root", str(repo.root)]) == 0
    for plugin_dir in (alpha, beta):
        copy = json.loads((plugin_dir / CLAUDE_MANIFEST).read_text(encoding="utf-8"))
        source = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
        assert source["$schema"] == SCHEMA_ID
        assert copy == {k: v for k, v in source.items() if k != "$schema"}


def test_check_reports_a_stale_claude_manifest(repo, capsys):
    plugin_dir = repo.add_plugin("emad-alpha")
    main(["--root", str(repo.root)])
    manifest = json.loads((plugin_dir / "plugin.json").read_text())
    manifest["version"] = "0.1.0"
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert main(["--root", str(repo.root), "--check"]) == 1
    out = capsys.readouterr()
    assert "plugins/emad-alpha/.claude-plugin/plugin.json (committed)" in out.out
    assert '+  "version": "0.1.0",' in out.out
    assert "just sync" in out.err


def test_check_reports_a_missing_claude_manifest(repo, capsys):
    plugin_dir = repo.add_plugin("emad-alpha")
    main(["--root", str(repo.root)])
    (plugin_dir / CLAUDE_MANIFEST).unlink()
    assert main(["--root", str(repo.root), "--check"]) == 1
    assert "plugins/emad-alpha/.claude-plugin/plugin.json" in capsys.readouterr().out


def test_the_real_catalogs_are_in_sync():
    assert main(["--check"]) == 0

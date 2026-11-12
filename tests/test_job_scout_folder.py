"""Tests for check_folder.py and for clean errors when the job search folder cannot be used."""

from __future__ import annotations

import os
import re
import shutil
import urllib.error

import pytest

from job_scout import ASSETS, job, load, write_jobs

check = load("check_folder")
tracker = load("tracker")
vendor_report = load("vendor_report")
poll_boards = load("poll_boards")


def _names(folder) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


@pytest.fixture
def read_only(tmp_path):
    """A job search folder with a tracker, a config and a profile that cannot be written to."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can write to a read-only folder")
    folder = tmp_path / "search"
    folder.mkdir()
    write_jobs(folder, [job()])
    shutil.copy(ASSETS / "search-config.template.json", folder / "search-config.json")
    shutil.copy(ASSETS / "profile.template.yaml", folder / "profile.yaml")
    folder.chmod(0o555)
    yield folder
    folder.chmod(0o755)


# --- check_folder.py: the folder ----------------------------------------------------------------


def test_a_missing_folder_fails_and_points_to_upload_mode(tmp_path, capsys):
    assert check.main(["--dir", str(tmp_path / "nope")]) == 1
    out = capsys.readouterr().out
    assert "does not exist" in out
    assert "upload mode" in out


def test_a_read_only_folder_fails_and_leaves_no_probe_file(read_only, capsys):
    before = _names(read_only)
    assert check.main(["--dir", str(read_only)]) == 1
    out = capsys.readouterr().out
    assert "cannot write" in out
    assert "upload mode" in out
    assert _names(read_only) == before


def test_a_writable_folder_passes_and_lists_what_is_missing(tmp_path, capsys):
    write_jobs(tmp_path, [job()])
    assert check.main(["--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert re.search(r"OK\s+can write here", out)
    assert re.search(r"OK\s+jobs\.json", out)
    assert re.search(r"MISSING\s+profile\.yaml.*intake", out)
    assert re.search(r"MISSING\s+search-config\.json.*--init", out)
    assert "cannot tell whether the folder stays" in out
    assert _names(tmp_path) == ["jobs.json"]


def test_the_check_names_a_missing_base_resume(tmp_path, capsys):
    write_jobs(tmp_path, [job()])
    (tmp_path / "profile.yaml").write_text("resume:\n  base_docx: base.docx\n", encoding="utf-8")
    assert check.main(["--dir", str(tmp_path)]) == 0
    assert re.search(r"MISSING\s+base resume.*base\.docx", capsys.readouterr().out)


def test_init_creates_a_new_folder_that_the_tracker_accepts(tmp_path, capsys):
    folder = tmp_path / "new-search"
    assert check.main(["--dir", str(folder), "--init"]) == 0
    for name in ("jobs.json", "search-config.json", "kanban.html"):
        assert (folder / name).is_file(), name
    for name in ("resumes", "backups", "outreach"):
        assert (folder / name).is_dir(), name
    # Intake writes profile.yaml. A copied template would look like a finished intake.
    assert not (folder / "profile.yaml").exists()
    assert "created jobs.json" in capsys.readouterr().out
    assert tracker.main(["--dir", str(folder), "validate"]) == 0


def test_init_never_overwrites_a_file(tmp_path, capsys):
    write_jobs(tmp_path, [job()])
    before = (tmp_path / "jobs.json").read_text(encoding="utf-8")
    assert check.main(["--dir", str(tmp_path), "--init"]) == 0
    assert (tmp_path / "jobs.json").read_text(encoding="utf-8") == before
    assert "kept jobs.json" in capsys.readouterr().out


# --- check_folder.py: tools and network --------------------------------------------------------


def test_the_tools_check_marks_missing_tools_and_which_are_optional():
    lines = check.check_tools(which=lambda name: None, has_module=lambda name: False)
    text = "\n".join(f"{line.status} {line.label} {line.note}" for line in lines)
    assert re.search(r"OK Python 3\.\d+", text)
    assert re.search(r"MISSING python-docx .*resume", text)
    assert re.search(r"MISSING LibreOffice .*optional", text)
    assert re.search(r"MISSING pdftotext .*optional", text)


def test_the_network_check_tells_reachable_hosts_from_blocked_ones():
    def fetch(url, timeout):
        if "ashbyhq" in url:
            return 200, {"jobs": []}
        if "greenhouse" in url:
            return 403, None
        if "lever" in url:
            raise urllib.error.URLError("no route to host")
        if "arbeitnow" in url:
            return 404, None
        raise ValueError("the answer was not JSON")

    lines = {line.label: line for line in check.check_network(fetch, timeout=1)}
    assert set(lines) == {
        "api.ashbyhq.com",
        "boards-api.greenhouse.io",
        "api.lever.co",
        "www.arbeitnow.com",
        "jobicy.com",
    }
    assert lines["api.ashbyhq.com"].status == "OK"
    assert lines["www.arbeitnow.com"].status == "OK"
    assert lines["boards-api.greenhouse.io"].status == "BLOCKED"
    assert "403" in lines["boards-api.greenhouse.io"].note
    assert lines["api.lever.co"].status == "BLOCKED"
    assert lines["jobicy.com"].status == "BLOCKED"


# --- clean errors in the other scripts -----------------------------------------------------------


def test_a_missing_tracker_says_how_to_set_up_a_folder(tmp_path, capsys):
    assert tracker.main(["--dir", str(tmp_path), "validate"]) == 1
    err = capsys.readouterr().err
    assert "jobs.json does not exist" in err
    assert "check_folder.py" in err and "--init" in err


def test_a_missing_folder_says_the_agent_cannot_see_it(tmp_path, capsys):
    assert tracker.main(["--dir", str(tmp_path / "nope"), "validate"]) == 1
    err = capsys.readouterr().err
    assert "does not exist" in err
    assert "upload mode" in err


def test_backup_in_a_read_only_folder_gives_a_clean_error(read_only, capsys):
    assert tracker.main(["--dir", str(read_only), "backup"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: cannot write")
    assert "check_folder.py" in err


def test_a_tracker_change_in_a_read_only_folder_gives_a_clean_error(read_only, capsys):
    args = ["--dir", str(read_only), "--today", "2026-11-10", "seen", "--id"]
    assert tracker.main([*args, "acme-staff-engineer"]) == 1
    assert capsys.readouterr().err.startswith("error: cannot write")


def test_the_vendor_report_in_a_read_only_folder_gives_a_clean_error(read_only, capsys):
    assert vendor_report.main(["--dir", str(read_only), "--out", "vendor-report.md"]) == 1
    assert capsys.readouterr().err.startswith("error: cannot write")


def test_poll_boards_in_a_read_only_folder_gives_a_clean_error(read_only, monkeypatch, capsys):
    monkeypatch.setattr(poll_boards, "poll", lambda *a, **k: {"boards": {}, "candidates": []})
    assert poll_boards.main(["--dir", str(read_only)]) == 1
    assert capsys.readouterr().err.startswith("error: cannot write")

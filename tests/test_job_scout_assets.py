"""Tests for the job-scout templates, the kanban board, the scripts' --help, and privacy."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from job_scout import ASSETS, SCRIPTS, SKILL, load

profile_yaml = load("profile_yaml")
tracker = load("tracker")
poll_boards = load("poll_boards")

COMMANDS = [
    "poll_boards",
    "tracker",
    "tailor_resume",
    "sync_resumes",
    "vendor_report",
    "profile_yaml",
    "check_folder",
]


def test_the_profile_template_parses_and_feeds_the_prefilter():
    profile = profile_yaml.load(ASSETS / "profile.template.yaml")
    for section in ("role", "work", "location", "money", "search", "resume"):
        assert isinstance(profile.get(section), dict), section
    assert profile_yaml.get(profile, "search.report_threshold") == 7
    assert profile_yaml.get(profile, "search.notify_only_on_news") is True
    assert profile_yaml.get(profile, "location.work_authorization") is None
    poll_boards.Rules.from_profile(profile)


def test_every_profile_field_has_a_comment():
    lines = (ASSETS / "profile.template.yaml").read_text(encoding="utf-8").splitlines()
    missing = []
    for n, line in enumerate(lines):
        stripped = line.strip()
        if not re.match(r"^[A-Za-z_][\w.-]*:", stripped):
            continue
        previous = lines[n - 1].strip() if n else ""
        if "#" not in line and not previous.startswith("#"):
            missing.append(stripped)
    assert missing == []


def test_the_jobs_template_is_a_valid_empty_tracker():
    data = json.loads((ASSETS / "jobs.template.json").read_text(encoding="utf-8"))
    assert data["jobs"] == []
    assert data["meta"]["statuses"] == ["new", "applied", "in_process", "rejected", "archived"]
    assert tracker.validate(data) == []


def test_the_search_config_template_starts_with_an_empty_registry():
    config = json.loads((ASSETS / "search-config.template.json").read_text(encoding="utf-8"))
    assert config["boards"] == {"ashby": [], "greenhouse": [], "lever": []}
    for kind, boards in config["starter_boards"].items():
        assert kind in ("ashby", "greenhouse", "lever")
        assert boards and all(b["token"] and b["company"] for b in boards)
    urls = [url for _, url, _, _ in poll_boards._jobs(config)]
    assert urls and all("arbeitnow" in u or "jobicy" in u for u in urls)
    for key in ("unresolved", "filter_refinements", "miss_log", "channel_platforms"):
        assert isinstance(config[key], list), key


def test_the_kanban_board_ships_without_data_and_respects_ownership():
    text = (ASSETS / "kanban.html").read_text(encoding="utf-8")
    seed = re.search(r"const SEED = (\{.*?\});", text, re.S)
    assert seed and json.loads(seed.group(1))["jobs"] == []
    assert 'by:"user"' in text
    assert "my_notes:" in text
    assert "showOpenFilePicker" in text


@pytest.mark.parametrize("name", COMMANDS)
def test_every_script_has_help(name):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / f"{name}.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=SCRIPTS,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower() or "Usage" in result.stdout


def test_the_skill_holds_no_personal_contact_details_or_local_paths():
    # Only reserved example domains (RFC 2606) may appear in the skill.
    allowed_email = re.compile(r"(@example\.(com|org|net)|\.example)$")
    problems = []
    for path in SKILL.rglob("*"):
        # Python writes compiled .pyc files into __pycache__/ when other tests import the
        # scripts. They are binary, git ignores them, and they never ship with the skill.
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(SKILL)
        for email in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text):
            if not allowed_email.search(email) and "@" not in email[:1]:
                problems.append(f"{rel}: email {email}")
        if re.search(r"/Users/|/home/\w+/", text):
            problems.append(f"{rel}: local path")
        if re.search(r"\+\d{2}[\s-]?\d{2,3}[\s-]?\d{3}[\s-]?\d{3,4}", text):
            problems.append(f"{rel}: phone number")
    assert problems == []


def test_the_kanban_board_rereads_the_file_before_every_change():
    text = (ASSETS / "kanban.html").read_text(encoding="utf-8")
    for function in ("moveJob", "saveDetails", "addJob"):
        body = text.split(f"async function {function}(", 1)[1].split("\n}\n", 1)[0]
        assert "await refresh()" in body, function


def test_the_profile_template_asks_about_the_contact_search():
    profile = profile_yaml.load(ASSETS / "profile.template.yaml")
    assert profile_yaml.get(profile, "outreach.find_contacts") == "ask"
    assert profile_yaml.get(profile, "outreach.max_per_run") == 3
    intake = (SKILL / "references" / "intake.md").read_text(encoding="utf-8")
    assert "outreach.find_contacts" in intake
    assert "hiring-contact-finder" in intake


def _kanban_function(name: str) -> str:
    text = (ASSETS / "kanban.html").read_text(encoding="utf-8")
    start = text.index(f"function {name}(")
    return text[start : text.index("\n}\n", start) + 2]


def test_the_kanban_board_lets_the_user_set_channel_and_human_contact():
    text = (ASSETS / "kanban.html").read_text(encoding="utf-8")
    vendor_report = load("vendor_report")
    for channel in vendor_report.CHANNELS:
        assert f'<option value="{channel}">' in text, channel
    assert 'id="d-channel"' in text and 'id="d-hc-set"' in text
    save = _kanban_function("saveDetails")
    assert "job.channel" in save and "human_contact_by" in save


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_kanban_board_keeps_a_human_contact_the_user_set():
    script = (
        _kanban_function("deriveHumanContact")
        + """
const cases = [
  {status: "rejected", history: [{status: "applied"}, {status: "rejected"}]},
  {status: "rejected", history: [{status: "applied"}, {status: "rejected"}],
   human_contact: true, human_contact_by: "user"},
  {status: "applied", history: [{status: "applied"}], human_contact: false,
   human_contact_by: "user"},
  {status: "rejected", history: [{status: "in_process"}, {status: "rejected"}],
   human_contact: false, human_contact_by: "user"},
  {status: "applied", history: [{status: "applied"}]},
];
console.log(JSON.stringify(cases.map(deriveHumanContact)));
"""
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == [None, True, False, True, None]


NODE = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _node(script: str, tz: str | None = None) -> str:
    env = {**os.environ, "TZ": tz} if tz else None
    out = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True, env=env
    )
    return out.stdout


@NODE
def test_the_board_names_the_same_vendor_as_the_scripts():
    jobfiles = load("jobfiles")
    urls = [f"https://acme.{domain}/jobs/1" for domain, _ in jobfiles.VENDOR_DOMAINS]
    urls += [
        "https://www.clever.com/careers/1",
        "https://acme.com/jobs/1?ref=https://jobs.lever.co/x",
        "https://careers.acme.com/j/1?gh_jid=123",
        "jobs.lever.co/acme/1",
        "https://acme.com/careers/1",
        "not a url",
        "",
    ]
    script = _kanban_function("detectVendor") + (
        f"console.log(JSON.stringify({json.dumps(urls)}.map(detectVendor)));"
    )
    assert json.loads(_node(script)) == [jobfiles.detect_vendor(u) for u in urls]


@NODE
@pytest.mark.parametrize(
    ("tz", "utc", "local"),
    [
        ("Pacific/Kiritimati", "2026-11-11T12:30:00Z", "2026-11-12"),
        ("America/Lima", "2026-11-12T02:00:00Z", "2026-11-11"),
    ],
)
def test_the_board_writes_the_local_date_not_the_utc_date(tz, utc, local):
    fake_now = (
        "const RealDate = Date; globalThis.Date = class extends RealDate { "
        f"constructor(...a) {{ super(...(a.length ? a : [{json.dumps(utc)}])); }} }};\n"
    )
    script = fake_now + _kanban_function("today") + "console.log(today());"
    assert _node(script, tz=tz).strip() == local


@NODE
def test_the_board_refuses_a_file_that_is_not_a_tracker():
    texts = ['{"boards": {}}', '{"jobs": "x"}', "{bad json", '{"meta": {}, "jobs": []}', "[]"]
    script = _kanban_function("parseTracker") + (
        f"console.log(JSON.stringify({json.dumps(texts)}.map(t => {{"
        " try { return parseTracker(t).jobs.length; } catch (e) { return 'error'; } })));"
    )
    assert json.loads(_node(script)) == ["error", "error", "error", 0, 0]


def test_the_board_connects_a_file_only_after_it_reads_as_a_tracker():
    body = _kanban_function("openFile")
    assert body.index("parseTracker(") < body.index("fileHandle = h")
    for name in ("refresh", "reloadFile"):
        assert "parseTracker(" in _kanban_function(name), name


@NODE
def test_the_board_links_only_web_addresses_and_shows_only_numeric_scores():
    urls = [
        "https://example.com/a",
        "HTTP://example.com",
        "javascript:alert(1)",
        " javascript:x",
        "data:text/html,x",
        "",
        None,
    ]
    scores = [8, "7", "<img src=x>", None, "", "8.5"]
    script = (
        _kanban_function("safeUrl")
        + _kanban_function("scoreOf")
        + (
            f"console.log(JSON.stringify([{json.dumps(urls)}.map(safeUrl),"
            f" {json.dumps(scores)}.map(scoreOf)]));"
        )
    )
    links, numbers = json.loads(_node(script))
    assert links == ["https://example.com/a", "HTTP://example.com", "", "", "", "", ""]
    assert numbers == [8, 7, None, None, None, 8.5]
    card = _kanban_function("cardEl")
    assert "safeUrl(job.url)" in card and "${job.score}" not in card

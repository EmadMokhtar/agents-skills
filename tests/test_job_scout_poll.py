"""Tests for the job-scout board poller. No test touches the network: fetching is replaced."""

from __future__ import annotations

import json

import pytest

from job_scout import load

poll_boards = load("poll_boards")

ASHBY = {
    "jobs": [
        {
            "id": "3f9d85f6-0750-400f-a129-6a0f8ab76476",
            "title": "Staff Engineer, Agents",
            "location": "Lisbon",
            "isRemote": False,
            "workplaceType": "Hybrid",
            "employmentType": "FullTime",
            "publishedAt": "2026-11-01T09:00:00.000+00:00",
            "isListed": True,
            "jobUrl": "https://jobs.ashbyhq.com/acme/3f9d85f6-0750-400f-a129-6a0f8ab76476",
            "applyUrl": "https://jobs.ashbyhq.com/acme/3f9d85f6-0750-400f-a129-6a0f8ab76476/application",
            "descriptionPlain": "Build agent tooling.",
            "compensation": {"compensationTierSummary": "€90K – €110K"},
        },
        {
            "id": "x",
            "title": "Hidden",
            "isListed": False,
            "jobUrl": "https://jobs.ashbyhq.com/acme/x",
        },
    ]
}
GREENHOUSE = {
    "jobs": [
        {
            "id": 4769511101,
            "title": "Sr. Backend Engineer",
            "location": {"name": "Remote - EMEA"},
            "absolute_url": "https://job-boards.eu.greenhouse.io/globex/jobs/4769511101",
            "first_published": "2026-10-30T10:00:00-04:00",
            "updated_at": "2026-11-02T10:00:00-04:00",
            "content": "&lt;p&gt;We hire in the UK, Czechia or Italy.&lt;/p&gt;",
        }
    ]
}
LEVER = [
    {
        "id": "abc",
        "text": "Principal Engineer",
        "categories": {"location": "Lisbon", "commitment": "Full-time"},
        "createdAt": 1761955200000,
        "hostedUrl": "https://jobs.lever.co/initech/abc",
        "applyUrl": "https://jobs.lever.co/initech/abc/apply",
        "descriptionPlain": "Lead the platform.",
        "workplaceType": "onsite",
    }
]
ARBEITNOW = {
    "data": [
        {
            "slug": "staff-engineer-acme-1",
            "company_name": "Acme",
            "title": "Staff Engineer, Agents",
            "description": "<p>Lead role</p>",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/companies/acme/staff-engineer-acme-1",
            "location": "Berlin",
            "created_at": 1761955200,
        }
    ]
}
JOBICY = {
    "jobs": [
        {
            "id": 1,
            "url": "https://jobicy.com/jobs/1-staff-engineer",
            "jobTitle": "Staff Engineer",
            "companyName": "Hooli",
            "jobGeo": "Europe",
            "pubDate": "2026-11-03 10:00:00",
            "jobDescription": "<p>Remote</p>",
        }
    ]
}


def test_ashby_postings_are_normalized_and_unlisted_ones_dropped():
    [p] = poll_boards.normalize_ashby("acme", "Acme", ASHBY)
    assert p["title"] == "Staff Engineer, Agents"
    assert p["company"] == "Acme"
    assert p["url"].endswith("3f9d85f6-0750-400f-a129-6a0f8ab76476")
    assert p["published"] == "2026-11-01"
    assert p["remote"] is False
    assert p["compensation"] == "€90K – €110K"
    assert p["lead"] is False
    assert p["source"] == "ashby" and p["token"] == "acme"  # noqa: S105 (a board token)


def test_greenhouse_content_is_unescaped_and_stripped():
    [p] = poll_boards.normalize_greenhouse("globex", "Globex", GREENHOUSE)
    # Normalizers keep the raw HTML; poll() cleans it only for postings it keeps.
    assert poll_boards.strip_html(p["description"]) == "We hire in the UK, Czechia or Italy."
    assert p["location"] == "Remote - EMEA"
    assert p["remote"] is True
    assert p["published"] == "2026-10-30"


def test_lever_dates_come_from_milliseconds():
    [p] = poll_boards.normalize_lever("initech", "Initech", LEVER)
    assert p["published"] == "2025-11-01"
    assert p["employment_type"] == "Full-time"
    assert p["url"] == "https://jobs.lever.co/initech/abc"


def test_aggregator_postings_are_leads_only():
    [a] = poll_boards.normalize_arbeitnow(ARBEITNOW)
    [j] = poll_boards.normalize_jobicy(JOBICY)
    assert a["lead"] is True and j["lead"] is True
    assert a["company"] == "Acme" and j["location"] == "Europe"
    assert poll_boards.strip_html(a["description"]) == "Lead role"


# --- the prefilter --------------------------------------------------------------------------

PROFILE = {
    "role": {
        "target_titles": ["Staff Software Engineer"],
        "excluded_titles": ["Manager", "Intern"],
        "lower_title_exception": {"title_level": "Senior", "allowed_at": ["Globex"]},
    },
    "search": {
        "title_keywords": ["Staff", "Principal", "Tech Lead", "Member of Technical Staff"],
        "location_keywords": ["Portugal", "Lisbon", "Europe", "EMEA"],
    },
}


def posting(title, company="Acme", location="Lisbon", remote=None) -> dict:
    return {"title": title, "company": company, "location": location, "remote": remote}


@pytest.fixture
def rules():
    return poll_boards.Rules.from_profile(PROFILE)


@pytest.mark.parametrize(
    "title",
    [
        "Staff Engineer",
        "AI Staff Engineer",
        "Staff / Senior Software Engineer",
        "Tech Lead, Backend",
        "Member of Technical Staff, Agents",
    ],
)
def test_keywords_match_anywhere_in_the_title(rules, title):
    assert poll_boards.keep(posting(title), rules)


def test_excluded_titles_win(rules):
    assert not poll_boards.keep(posting("Staff Engineering Manager"), rules)


def test_lower_title_passes_only_at_listed_companies(rules):
    assert not poll_boards.keep(posting("Senior Backend Engineer", company="Initech"), rules)
    assert poll_boards.keep(posting("Sr Backend Engineer II", company="Globex"), rules)


def test_location_keywords_keep_remote_and_unknown_locations(rules):
    assert poll_boards.keep(posting("Staff Engineer", location="Remote - Worldwide"), rules)
    assert poll_boards.keep(posting("Staff Engineer", location=""), rules)
    assert poll_boards.keep(posting("Staff Engineer", location="Austin", remote=True), rules)
    assert not poll_boards.keep(posting("Staff Engineer", location="Austin, TX"), rules)


def test_without_search_keywords_the_profile_titles_are_used():
    rules = poll_boards.Rules.from_profile({"role": {"target_titles": ["Staff Software Engineer"]}})
    assert poll_boards.keep(posting("Staff Software Engineer, Platform", location="Austin"), rules)
    assert not poll_boards.keep(posting("Software Engineer"), rules)


# --- polling --------------------------------------------------------------------------------

CONFIG = {
    "boards": {
        "ashby": [{"token": "acme", "company": "Acme"}, {"token": "gone", "company": "Gone"}],
        "greenhouse": [{"token": "globex", "company": "Globex"}],
        "lever": [{"token": "initech", "company": "Initech"}],
    },
    "aggregators": {
        "arbeitnow": {"enabled": True, "pages": 1},
        "jobicy": {"enabled": False, "queries": ["count=50"]},
    },
}


def fake_fetch(url, timeout):
    if "job-board/gone" in url:
        return 404, None
    if "ashbyhq" in url:
        return 200, ASHBY
    if "greenhouse" in url:
        return 200, GREENHOUSE
    if "lever" in url:
        return 200, LEVER
    if "arbeitnow" in url:
        return 200, ARBEITNOW
    raise AssertionError(f"unexpected fetch {url}")


def test_poll_reports_dead_tokens_and_keeps_matching_postings(rules):
    result = poll_boards.poll(CONFIG, rules, fake_fetch, workers=2, timeout=5)
    assert result["boards"]["ashby:gone"] == {"status": "dead", "http": 404}
    assert result["boards"]["ashby:acme"] == {"status": "ok", "jobs": 1, "kept": 1}
    assert result["boards"]["arbeitnow:page-1"]["status"] == "ok"
    titles = sorted((c["source"], c["title"]) for c in result["candidates"])
    assert titles == [
        ("arbeitnow", "Staff Engineer, Agents"),
        ("ashby", "Staff Engineer, Agents"),
        ("greenhouse", "Sr. Backend Engineer"),
        ("lever", "Principal Engineer"),
    ]


def test_poll_survives_a_board_that_raises(rules):
    def flaky(url, timeout):
        if "greenhouse" in url:
            raise TimeoutError("timed out")
        return fake_fetch(url, timeout)

    result = poll_boards.poll(CONFIG, rules, flaky, workers=2, timeout=5)
    assert result["boards"]["greenhouse:globex"] == {"status": "error", "error": "timed out"}


def test_the_command_writes_candidates_inside_the_folder(tmp_path, monkeypatch, capsys):
    (tmp_path / "profile.yaml").write_text(
        "search:\n  title_keywords:\n    - Staff\n    - Principal\n", encoding="utf-8"
    )
    (tmp_path / "search-config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    monkeypatch.setattr(poll_boards, "fetch_json", fake_fetch)
    assert poll_boards.main(["--dir", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "candidates.json").read_text())
    assert len(data["candidates"]) == 3
    out = capsys.readouterr().out
    assert "dead: ashby:gone" in out
    assert "Staff Engineer, Agents" not in out


def test_only_https_urls_are_fetched():
    with pytest.raises(ValueError, match="https"):
        poll_boards.fetch_json("http://example.com/api", timeout=1)


def test_a_board_with_an_unexpected_payload_does_not_stop_the_poll(rules):
    def odd(url, timeout):
        if "job-board/acme" in url:
            return 200, {"jobs": None}
        return fake_fetch(url, timeout)

    result = poll_boards.poll(CONFIG, rules, odd, workers=2, timeout=5)
    assert result["boards"]["ashby:acme"]["status"] == "error"
    assert result["boards"]["greenhouse:globex"]["status"] == "ok"


def test_poll_cleans_the_description_only_of_postings_it_keeps(rules, monkeypatch):
    calls = []
    real = poll_boards.strip_html
    monkeypatch.setattr(poll_boards, "strip_html", lambda text: calls.append(text) or real(text))
    office = {**GREENHOUSE["jobs"][0], "id": 999, "title": "Office Manager"}
    with_office = {**GREENHOUSE, "jobs": [*GREENHOUSE["jobs"], office]}

    def fetch(url, timeout):
        return (200, with_office) if "greenhouse" in url else fake_fetch(url, timeout)

    result = poll_boards.poll(CONFIG, rules, fetch, workers=2, timeout=5)
    seen = sum(b.get("jobs", 0) for b in result["boards"].values())
    assert seen > len(result["candidates"])  # some postings were dropped by the prefilter
    assert len(calls) == len(result["candidates"])
    assert all("<" not in c["description"] for c in result["candidates"])


def test_the_command_fails_when_no_board_could_be_read(tmp_path, monkeypatch, capsys):
    (tmp_path / "profile.yaml").write_text(
        "search:\n  title_keywords:\n    - Staff\n", encoding="utf-8"
    )
    (tmp_path / "search-config.json").write_text(json.dumps(CONFIG), encoding="utf-8")

    def blocked(url, timeout):
        raise OSError("blocked by a proxy")

    monkeypatch.setattr(poll_boards, "fetch_json", blocked)
    assert poll_boards.main(["--dir", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "no board could be read" in err
    assert "check_folder.py" in err

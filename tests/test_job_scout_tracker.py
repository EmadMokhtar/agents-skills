"""Tests for the job-scout tracker script: dedup, the relist rule, safe writes and validation."""

from __future__ import annotations

import json

import pytest

from job_scout import job, load, read_jobs, write_jobs

tracker = load("tracker")

TODAY = "2026-11-10"
ASHBY_URL = "https://jobs.ashbyhq.com/acme/3f9d85f6-0750-400f-a129-6a0f8ab76476"


def candidate(**fields) -> dict:
    entry = {
        "source": "ashby",
        "token": "acme",
        "company": "Acme",
        "title": "Staff Engineer",
        "location": "Remote - Europe",
        "url": ASHBY_URL,
        "published": "2026-11-01",
        "lead": False,
    }
    entry.update(fields)
    return entry


def run(folder, *args) -> int:
    return tracker.main(["--dir", str(folder), "--today", TODAY, *args])


# --- keys -----------------------------------------------------------------------------------


def test_normalize_url_drops_tracking_but_keeps_job_ids():
    assert tracker.normalize_url("HTTPS://Jobs.AshbyHQ.com/acme/ABC/?utm_source=x#apply") == (
        "https://jobs.ashbyhq.com/acme/ABC"
    )
    assert tracker.normalize_url("https://acme.com/careers/j/1?gh_jid=4977893101&utm=1") == (
        "https://acme.com/careers/j/1?gh_jid=4977893101"
    )


def test_job_ids_finds_uuids_greenhouse_ids_and_long_numbers():
    assert tracker.job_ids(ASHBY_URL) == {"3f9d85f6-0750-400f-a129-6a0f8ab76476"}
    assert tracker.job_ids("https://job-boards.eu.greenhouse.io/acme/jobs/4769511101") == {
        "4769511101"
    }
    assert tracker.job_ids("https://careers.acme.com/jobs?gh_jid=8462016002") == {"8462016002"}
    assert tracker.job_ids("https://acme.com/careers/2026/staff") == set()


def test_title_key_treats_sr_as_senior_and_ignores_punctuation():
    assert tracker.title_key("Acme", "Sr. AI Engineer") == tracker.title_key(
        "ACME", "Senior AI Engineer"
    )
    assert tracker.title_key("Acme", "Staff Engineer - Agents") == tracker.title_key(
        "Acme", "Staff Engineer, Agents"
    )


# --- classify -------------------------------------------------------------------------------


def test_a_url_already_tracked_as_rejected_is_not_new():
    jobs = [job(status="rejected")]
    result = tracker.classify([candidate()], jobs)
    assert result["new"] == []
    assert result["known"][0]["match"] == {
        "id": "acme-staff-engineer",
        "status": "rejected",
        "by": "url",
    }


def test_the_same_job_id_on_another_host_is_known():
    jobs = [job()]
    other = candidate(url="https://acme.com/careers?ashby_jid=3f9d85f6-0750-400f-a129-6a0f8ab76476")
    assert tracker.classify([other], jobs)["known"][0]["match"]["by"] == "job_id"


def test_a_repost_under_a_new_id_is_known_by_company_and_title():
    jobs = [job(status="archived")]
    repost = candidate(url="https://jobs.ashbyhq.com/acme/0b6f0d4e-1111-4222-8333-944455556666")
    result = tracker.classify([repost], jobs)
    assert result["new"] == []
    assert result["known"][0]["match"]["by"] == "company_title"


def expired(**fields) -> dict:
    return job(
        status="archived",
        title="Senior Software Engineer - DevX",
        published="2026-09-24",
        history=[
            {"status": "new", "date": "2026-09-25", "by": "agent"},
            {
                "status": "archived",
                "from": "new",
                "date": "2026-10-30",
                "by": "agent",
                "reason": "expired",
            },
        ],
        **fields,
    )


def test_a_url_the_agent_archived_as_expired_is_relisted_when_its_title_changed():
    live = candidate(title="Staff Platform Engineer", published="2026-10-29")
    result = tracker.classify([live], [expired()])
    assert [c["title"] for c in result["relisted"]] == ["Staff Platform Engineer"]
    assert result["relisted"][0]["match"]["id"] == "acme-staff-engineer"


def test_a_url_the_agent_archived_as_expired_is_relisted_when_only_the_date_changed():
    live = candidate(title="Senior Software Engineer - DevX", published="2026-10-29")
    assert len(tracker.classify([live], [expired()])["relisted"]) == 1


def test_an_unchanged_expired_url_is_only_known():
    live = candidate(title="Senior Software Engineer - DevX", published="2026-09-24")
    result = tracker.classify([live], [expired()])
    assert result["relisted"] == []
    assert result["known"][0]["match"]["by"] == "url"


def test_a_url_the_user_archived_is_never_relisted():
    user_archived = expired()
    user_archived["history"][-1] = {"status": "archived", "from": "new", "date": "2026-10-30"}
    live = candidate(title="Staff Platform Engineer", published="2026-10-29")
    result = tracker.classify([live], [user_archived])
    assert result["relisted"] == []
    assert len(result["known"]) == 1


def test_duplicate_candidates_keep_the_ats_posting_over_the_aggregator_lead():
    lead = candidate(source="arbeitnow", lead=True, url="https://www.arbeitnow.com/jobs/acme-1")
    ats = candidate()
    result = tracker.classify([lead, ats], [])
    assert [c["source"] for c in result["new"]] == ["ashby"]
    assert result["known"][0]["match"]["by"] == "candidate"


# --- writes ---------------------------------------------------------------------------------


def test_add_writes_a_new_entry_with_history_and_an_empty_my_notes(tmp_path):
    write_jobs(tmp_path, [])
    entries = tmp_path / "add.json"
    entries.write_text(
        json.dumps([{"title": "Staff Engineer", "company": "Acme", "url": ASHBY_URL}])
    )
    assert run(tmp_path, "add", "--file", str(entries)) == 0
    [added] = read_jobs(tmp_path)
    assert added["id"] == "acme-staff-engineer"
    assert added["status"] == "new"
    assert added["my_notes"] == ""
    assert added["vendor"] == "Ashby"
    assert added["first_seen"] == TODAY
    assert added["history"] == [{"status": "new", "date": TODAY, "by": "agent"}]
    assert (tmp_path / "backups" / f"jobs.backup-{TODAY}.json").is_file()


def test_add_refuses_a_duplicate_and_writes_nothing(tmp_path, capsys):
    write_jobs(tmp_path, [job(status="rejected")])
    before = (tmp_path / "jobs.json").read_text()
    entries = tmp_path / "add.json"
    entries.write_text(json.dumps({"title": "Staff Engineer", "company": "Acme", "url": ASHBY_URL}))
    assert run(tmp_path, "add", "--file", str(entries)) == 1
    assert (tmp_path / "jobs.json").read_text() == before
    assert "already tracked" in capsys.readouterr().err


@pytest.mark.parametrize("field", [{"my_notes": "mine"}, {"status": "applied"}])
def test_add_refuses_user_owned_fields(tmp_path, field):
    write_jobs(tmp_path, [])
    entries = tmp_path / "add.json"
    entries.write_text(json.dumps([{"title": "T", "company": "C", "url": ASHBY_URL, **field}]))
    assert run(tmp_path, "add", "--file", str(entries)) == 1
    assert read_jobs(tmp_path) == []


def test_archive_records_who_and_why(tmp_path):
    write_jobs(tmp_path, [job()])
    assert run(tmp_path, "archive", "--id", "acme-staff-engineer", "--reason", "expired") == 0
    [entry] = read_jobs(tmp_path)
    assert entry["status"] == "archived"
    assert entry["history"][-1] == {
        "status": "archived",
        "from": "new",
        "date": TODAY,
        "by": "agent",
        "reason": "expired",
    }


@pytest.mark.parametrize("status", ["applied", "in_process", "rejected", "archived"])
def test_archive_never_changes_a_status_the_user_set(tmp_path, status, capsys):
    write_jobs(tmp_path, [job(status=status, my_notes="keep me")])
    before = (tmp_path / "jobs.json").read_text()
    assert run(tmp_path, "archive", "--id", "acme-staff-engineer", "--reason", "expired") == 1
    assert (tmp_path / "jobs.json").read_text() == before
    assert "set by the user" in capsys.readouterr().err


def test_revive_moves_an_expired_role_back_to_new_and_keeps_my_notes(tmp_path):
    write_jobs(tmp_path, [expired(my_notes="keep me")])
    code = run(
        tmp_path,
        "revive",
        "--id",
        "acme-staff-engineer",
        "--title",
        "Staff Platform Engineer",
        "--published",
        "2026-10-29",
    )
    assert code == 0
    [entry] = read_jobs(tmp_path)
    assert entry["status"] == "new"
    assert entry["title"] == "Staff Platform Engineer"
    assert entry["published"] == "2026-10-29"
    assert entry["my_notes"] == "keep me"
    last = entry["history"][-1]
    assert last["status"] == "new" and last["from"] == "archived" and last["reason"] == "relisted"
    assert "Senior Software Engineer - DevX" in last["detail"]


def test_revive_refuses_a_role_the_user_archived(tmp_path):
    entry = expired()
    entry["history"][-1].pop("by")
    write_jobs(tmp_path, [entry])
    assert run(tmp_path, "revive", "--id", "acme-staff-engineer") == 1
    assert read_jobs(tmp_path)[0]["status"] == "archived"


def test_seen_updates_last_verified_only(tmp_path):
    write_jobs(tmp_path, [job()])
    assert run(tmp_path, "seen", "--id", "acme-staff-engineer") == 0
    [entry] = read_jobs(tmp_path)
    assert entry["last_verified"] == TODAY
    assert entry["status"] == "new"


def test_backup_never_overwrites_an_earlier_backup(tmp_path):
    write_jobs(tmp_path, [])
    (tmp_path / "job-search.md").write_text("# Log\n")
    assert run(tmp_path, "backup") == 0
    assert run(tmp_path, "backup") == 0
    names = sorted(p.name for p in (tmp_path / "backups").iterdir())
    assert len([n for n in names if n.startswith("jobs.backup-")]) == 2
    assert f"job-search.backup-{TODAY}.md" in names


def test_dedup_writes_a_result_file_and_prints_only_counts(tmp_path, capsys):
    write_jobs(tmp_path, [job(status="rejected")])
    (tmp_path / "candidates.json").write_text(
        json.dumps(
            {
                "candidates": [
                    candidate(),
                    candidate(url="https://jobs.lever.co/acme/9", title="Staff SRE"),
                ]
            }
        )
    )
    assert run(tmp_path, "dedup") == 0
    result = json.loads((tmp_path / "dedup.json").read_text())
    assert [c["title"] for c in result["new"]] == ["Staff SRE"]
    out = capsys.readouterr().out
    assert "new: 1" in out and "known: 1" in out and "Staff SRE" not in out


# --- validate -------------------------------------------------------------------------------


def test_validate_passes_a_good_tracker(tmp_path):
    write_jobs(tmp_path, [job()])
    assert run(tmp_path, "validate") == 0


def test_validate_reports_each_problem(tmp_path, capsys):
    bad = job(status="maybe", history=[{"status": "new", "date": "2026-11-02"}])
    twin = job(id="acme-staff-engineer", first_seen="11/02/2026")
    del twin["my_notes"]
    write_jobs(tmp_path, [bad, twin])
    assert run(tmp_path, "validate") == 1
    err = capsys.readouterr().err
    assert "unknown status 'maybe'" in err
    assert "duplicate id" in err
    assert "duplicate url" in err
    assert "missing field 'my_notes'" in err
    assert "first_seen" in err
    assert "last history entry" in err


def test_writes_stay_inside_the_chosen_folder(tmp_path):
    folder = tmp_path / "search"
    folder.mkdir()
    write_jobs(folder, [])
    (folder / "candidates.json").write_text(json.dumps({"candidates": [candidate()]}))
    outside = tmp_path / "elsewhere.json"
    assert run(folder, "dedup", "--out", str(outside)) == 1
    assert not outside.exists()


# --- review fixes: separate openings, leads, ids per company -----------------------------


def test_the_same_title_in_another_location_is_a_separate_role():
    elsewhere = candidate(
        url="https://jobs.ashbyhq.com/acme/0b6f0d4e-1111-4222-8333-944455556666",
        location="San Francisco",
    )
    result = tracker.classify([elsewhere], [job(status="rejected")])
    assert [c["location"] for c in result["new"]] == ["San Francisco"]


def test_two_ats_postings_with_one_title_in_two_places_are_both_new():
    lisbon = candidate(location="Lisbon")
    austin = candidate(
        url="https://jobs.ashbyhq.com/acme/0b6f0d4e-1111-4222-8333-944455556666",
        location="Austin",
    )
    assert len(tracker.classify([lisbon, austin], [])["new"]) == 2


def test_a_lead_matches_the_ats_posting_even_with_another_location_string():
    lead = candidate(
        source="arbeitnow",
        lead=True,
        url="https://www.arbeitnow.com/jobs/acme-1",
        location="Lisbon",
    )
    ats = candidate(location="Lisbon, Portugal")
    result = tracker.classify([lead, ats], [])
    assert [c["source"] for c in result["new"]] == ["ashby"]


def test_a_lead_for_a_tracked_role_is_known():
    lead = candidate(
        source="jobicy", lead=True, url="https://jobicy.com/jobs/1-staff", location="Europe"
    )
    result = tracker.classify([lead], [job(status="rejected")])
    assert result["known"][0]["match"]["by"] == "company_title"


def test_numeric_job_ids_match_only_within_one_company():
    tracked = job(url="https://acme.wd1.myworkdayjobs.com/careers/job/JR123456")
    other = candidate(
        company="Globex",
        title="Platform Engineer",
        url="https://globex.wd5.myworkdayjobs.com/jobs/job/JR123456",
    )
    assert len(tracker.classify([other], [tracked])["new"]) == 1

"""Tests for the job-scout vendor report: which hiring software each application went through."""

from __future__ import annotations

import json

import pytest

from job_scout import job, load, read_jobs, write_jobs

vendor_report = load("vendor_report")


@pytest.mark.parametrize(
    ("url", "vendor"),
    [
        ("https://jobs.ashbyhq.com/acme/1", "Ashby"),
        ("https://job-boards.eu.greenhouse.io/acme/jobs/1", "Greenhouse"),
        ("https://jobs.lever.co/acme/1", "Lever"),
        ("https://acme.wd3.myworkdayjobs.com/x", "Workday"),
        ("https://careers.acme.com/jobs/j/1?gh_jid=123", "Greenhouse"),
        ("https://acme.com/careers/1", "company-own"),
        ("", "unknown"),
    ],
)
def test_detect_vendor(url, vendor):
    assert vendor_report.detect_vendor(url) == vendor


def test_human_contact_comes_from_the_history():
    reached = job(status="rejected", history=[{"status": "in_process"}, {"status": "rejected"}])
    ghosted = job(status="rejected", history=[{"status": "applied"}, {"status": "rejected"}])
    waiting = job(status="applied", history=[{"status": "applied"}])
    assert vendor_report.derive_human_contact(reached) is True
    assert vendor_report.derive_human_contact(ghosted) is False
    assert vendor_report.derive_human_contact(waiting) is None


def rejected(company: str, vendor: str = "Greenhouse", human=False) -> dict:
    return job(
        id=company.lower(),
        company=company,
        url=f"https://boards.greenhouse.io/{company.lower()}/jobs/1",
        status="rejected",
        vendor=vendor,
        human_contact=human,
        history=[{"status": "applied"}, {"status": "rejected"}],
    )


def test_three_rejections_with_no_human_contact_flag_the_vendor():
    text = vendor_report.report([rejected("Acme"), rejected("Globex"), rejected("Initech")])
    assert "| Greenhouse | routing | 3 | 3 | 3 | 0 | **FLAGGED** |" in text
    assert "hiring-contact-finder" in text


def test_one_human_contact_clears_the_flag():
    jobs = [rejected("Acme"), rejected("Globex"), rejected("Initech", human=True)]
    assert "FLAGGED" not in vendor_report.report(jobs)


def test_unknown_human_contact_makes_the_flag_provisional():
    jobs = [rejected("Acme"), rejected("Globex"), rejected("Initech", human=None)]
    jobs[2]["history"] = []
    assert "PROVISIONAL" in vendor_report.report(jobs)


def test_new_roles_are_not_counted_as_applications():
    assert "Applications counted: 0" in vendor_report.report([job()])


def test_fill_adds_missing_fields_and_never_overwrites(tmp_path):
    keep = job(id="keep", vendor="iCIMS", channel="referral")
    bare = job(id="bare", url="https://jobs.lever.co/acme/2")
    for field in ("vendor", "channel", "human_contact"):
        del bare[field]
    write_jobs(tmp_path, [keep, bare])
    assert vendor_report.main(["--dir", str(tmp_path), "--fill", "--today", "2026-11-10"]) == 0
    by_id = {j["id"]: j for j in read_jobs(tmp_path)}
    assert by_id["keep"]["vendor"] == "iCIMS" and by_id["keep"]["channel"] == "referral"
    assert by_id["bare"]["vendor"] == "Lever"
    assert by_id["bare"]["channel"] == "portal"
    assert by_id["bare"]["human_contact"] is None


def test_report_is_written_inside_the_folder(tmp_path):
    write_jobs(tmp_path, [rejected("Acme")])
    assert vendor_report.main(["--dir", str(tmp_path), "--out", "vendor-report.md"]) == 0
    assert (tmp_path / "vendor-report.md").read_text().startswith("# Vendor report")
    assert vendor_report.main(["--dir", str(tmp_path), "--out", str(tmp_path.parent / "x.md")]) == 1
    json.loads((tmp_path / "jobs.json").read_text())


def test_a_human_contact_the_user_set_is_kept():
    told = rejected("Acme", human=True)
    told["human_contact_by"] = "user"
    assert vendor_report.derive_human_contact(told) is True


def test_the_report_shows_which_channel_reached_a_human():
    referral = job(
        id="globex",
        company="Globex",
        status="in_process",
        channel="referral",
        history=[{"status": "applied"}, {"status": "in_process"}],
    )
    portal = [rejected("Acme"), rejected("Initech"), rejected("Hooli")]
    for entry in portal:
        entry["channel"] = "portal"
    text = vendor_report.report([*portal, referral])
    assert "## By channel" in text
    assert "| portal | 3 | 0 | 3 | 0 |" in text
    assert "| referral | 1 | 1 | 0 | 0 |" in text


def test_an_unknown_channel_is_listed_as_it_is():
    entry = rejected("Acme")
    entry["channel"] = "ATS (Ashby)"
    text = vendor_report.report([entry])
    assert "| ATS (Ashby) (not a known channel) | 1 |" in text


def test_a_company_page_takes_the_vendor_seen_on_its_other_postings(tmp_path):
    tagged = rejected("Vandelay")
    tagged.update(
        id="v1", url="https://careers.vandelay.com/jobs/1?gh_jid=111", vendor="Greenhouse"
    )
    plain = rejected("Vandelay")
    plain.update(id="v2", url="https://careers.vandelay.com/jobs/2", vendor="company-own")
    mixed = rejected("Kramerica")
    mixed.update(id="k1", url="https://kramerica.com/jobs/1", vendor="company-own")
    text = vendor_report.report([tagged, plain, mixed])
    assert "| Greenhouse | routing | 2 |" in text
    write_jobs(tmp_path, [tagged, plain, mixed])
    assert vendor_report.main(["--dir", str(tmp_path), "--fill", "--today", "2026-11-10"]) == 0
    by_id = {j["id"]: j for j in read_jobs(tmp_path)}
    assert by_id["v2"]["vendor"] == "Greenhouse" and by_id["v2"]["vendor_inferred"] is True
    assert by_id["k1"]["vendor"] == "company-own" and "vendor_inferred" not in by_id["k1"]
    assert "vendor_inferred" not in by_id["v1"]


def test_the_report_names_its_source():
    text = vendor_report.report([rejected("Acme")])
    assert "hai.stanford.edu" in text

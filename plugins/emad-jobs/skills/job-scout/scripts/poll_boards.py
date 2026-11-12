#!/usr/bin/env python3
"""Poll every job board in search-config.json and write the matching postings to candidates.json.

It reads two files from the job search folder (--dir):

  search-config.json  the board registry: Ashby, Greenhouse and Lever tokens, and the
                      aggregators (Arbeitnow, Jobicy) to use as leads
  profile.yaml        the person's criteria; only the title and location parts are used here

It polls the boards in parallel, keeps postings whose title and location pass a loose
prefilter, and writes candidates.json. The agent then applies the full criteria. It prints
only counts and the boards that failed, so the output stays small.

A posting from an ATS board (Ashby, Greenhouse, Lever) is live, because the board lists only
open roles. A posting from an aggregator is a lead: confirm it on the company's own board.

Usage:
  python3 poll_boards.py --dir ~/job-search
  python3 poll_boards.py --dir ~/job-search --workers 8 --timeout 20
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from jobfiles import FolderError, os_problem, read_json, resolve_in, write_json
from profile_yaml import ProfileError, get, load

ENDPOINTS = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
}
ARBEITNOW = "https://www.arbeitnow.com/api/job-board-api?page={page}"
JOBICY = "https://jobicy.com/api/v2/remote-jobs?{query}"
USER_AGENT = "job-scout/1.0 (job search skill; polls public job board APIs)"
MAX_DESCRIPTION = 20000
REMOTE_WORDS = ("remote", "anywhere", "worldwide", "distributed")


# --- fetching ---------------------------------------------------------------------------------


def fetch_json(url: str, timeout: float):
    """GET a public JSON API. Return (http status, parsed JSON or None)."""
    if not url.startswith("https://"):
        raise ValueError(f"only https URLs are fetched, not {url!r}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https only, checked above)
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None


# --- normalizing ------------------------------------------------------------------------------


def strip_html(text: str | None) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<(br|/p|/li|/h\d)\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)[:MAX_DESCRIPTION]


def _day(value) -> str | None:
    """Turn an ISO timestamp, a 'YYYY-MM-DD hh:mm' string or epoch seconds into YYYY-MM-DD."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10**11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()  # noqa: UP017 (runs on Python 3.9+)
    match = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    return match.group(1) if match else None


def _is_remote(location: str | None, flag=None):
    if flag is not None:
        return bool(flag)
    if location and any(w in location.lower() for w in REMOTE_WORDS):
        return True
    return None


def _posting(source, token, company, title, location, url, **extra) -> dict:
    return {
        "source": source,
        "token": token,
        "company": company,
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "remote": extra.pop("remote", None),
        "url": url,
        "apply_url": extra.pop("apply_url", None) or url,
        "published": extra.pop("published", None),
        "compensation": extra.pop("compensation", None),
        "employment_type": extra.pop("employment_type", None),
        "workplace": extra.pop("workplace", None),
        "description": extra.pop("description", ""),
        "lead": extra.pop("lead", False),
    }


def normalize_ashby(token: str, company: str, payload: dict) -> list[dict]:
    out = []
    for j in payload.get("jobs", []):
        if j.get("isListed") is False:
            continue
        comp = j.get("compensation") or {}
        locations = [j.get("location")] + [
            s.get("location") for s in j.get("secondaryLocations") or [] if isinstance(s, dict)
        ]
        location = "; ".join(x for x in locations if x)
        out.append(
            _posting(
                "ashby",
                token,
                company,
                j.get("title"),
                location,
                j.get("jobUrl"),
                remote=_is_remote(location, j.get("isRemote")),
                apply_url=j.get("applyUrl"),
                published=_day(j.get("publishedAt")),
                compensation=comp.get("compensationTierSummary")
                or comp.get("scrapeableCompensationSalarySummary"),
                employment_type=j.get("employmentType"),
                workplace=j.get("workplaceType"),
                description=strip_html(j.get("descriptionPlain") or j.get("descriptionHtml")),
            )
        )
    return out


def normalize_greenhouse(token: str, company: str, payload: dict) -> list[dict]:
    out = []
    for j in payload.get("jobs", []):
        location = (j.get("location") or {}).get("name", "")
        out.append(
            _posting(
                "greenhouse",
                token,
                company,
                j.get("title"),
                location,
                j.get("absolute_url"),
                remote=_is_remote(location),
                published=_day(j.get("first_published") or j.get("updated_at")),
                description=strip_html(j.get("content")),
            )
        )
    return out


def normalize_lever(token: str, company: str, payload: list) -> list[dict]:
    out = []
    for j in payload if isinstance(payload, list) else []:
        cats = j.get("categories") or {}
        location = cats.get("location") or ", ".join(cats.get("allLocations") or [])
        salary = j.get("salaryRange") or {}
        comp = None
        if salary.get("min") and salary.get("max"):
            comp = f"{salary['min']}-{salary['max']} {salary.get('currency', '')}".strip()
        out.append(
            _posting(
                "lever",
                token,
                company,
                j.get("text"),
                location,
                j.get("hostedUrl"),
                remote=_is_remote(location, True if j.get("workplaceType") == "remote" else None),
                apply_url=j.get("applyUrl"),
                published=_day(j.get("createdAt")),
                compensation=comp,
                employment_type=cats.get("commitment"),
                workplace=j.get("workplaceType"),
                description=strip_html(j.get("descriptionPlain") or j.get("description")),
            )
        )
    return out


def normalize_arbeitnow(payload: dict) -> list[dict]:
    return [
        _posting(
            "arbeitnow",
            None,
            j.get("company_name", ""),
            j.get("title"),
            j.get("location"),
            j.get("url"),
            remote=bool(j.get("remote")),
            published=_day(j.get("created_at")),
            employment_type=", ".join(j.get("job_types") or []) or None,
            description=strip_html(j.get("description")),
            lead=True,
        )
        for j in payload.get("data", [])
    ]


def normalize_jobicy(payload: dict) -> list[dict]:
    out = []
    for j in payload.get("jobs", []):
        comp = None
        if j.get("annualSalaryMin") and j.get("annualSalaryMax"):
            comp = f"{j['annualSalaryMin']}-{j['annualSalaryMax']} {j.get('salaryCurrency', '')}"
        out.append(
            _posting(
                "jobicy",
                None,
                j.get("companyName", ""),
                j.get("jobTitle"),
                j.get("jobGeo"),
                j.get("url"),
                remote=True,
                published=_day(j.get("pubDate")),
                compensation=comp.strip() if comp else None,
                employment_type=", ".join(j.get("jobType") or []) or None,
                description=strip_html(j.get("jobDescription") or j.get("jobExcerpt")),
                lead=True,
            )
        )
    return out


NORMALIZERS = {
    "ashby": normalize_ashby,
    "greenhouse": normalize_greenhouse,
    "lever": normalize_lever,
}


# --- the prefilter ----------------------------------------------------------------------------


def _words(text: str | None) -> str:
    text = re.sub(r"[^\w]+", " ", (text or "").lower())
    text = re.sub(r"\b(sr|snr)\b", "senior", text)
    return f" {' '.join(text.split())} "


def _has(text_words: str, phrase: str) -> bool:
    phrase_words = _words(phrase).strip()
    return bool(phrase_words) and f" {phrase_words} " in text_words


class Rules:
    """The loose title and location prefilter, built from profile.yaml."""

    def __init__(self, keywords, excluded, lower_level, lower_companies, locations):
        self.keywords = list(keywords)
        self.excluded = list(excluded)
        self.lower_level = lower_level
        self.lower_companies = {_words(c).strip() for c in lower_companies}
        self.locations = list(locations)

    @classmethod
    def from_profile(cls, profile: dict) -> Rules:
        keywords = get(profile, "search.title_keywords", []) or (
            get(profile, "role.target_titles", []) + get(profile, "role.equivalent_titles", [])
        )
        return cls(
            keywords=keywords,
            excluded=get(profile, "role.excluded_titles", []),
            lower_level=get(profile, "role.lower_title_exception.title_level"),
            lower_companies=get(profile, "role.lower_title_exception.allowed_at", []),
            locations=get(profile, "search.location_keywords", []),
        )


def keep(posting: dict, rules: Rules) -> bool:
    """Keep a posting whose title and location could fit. The agent judges the rest.

    Keywords match anywhere in the title, never only at the start, so "AI Staff Engineer"
    and "Staff / Senior Engineer" pass. "Sr" and "Snr" count as "Senior".
    """
    title = _words(posting.get("title"))
    if any(_has(title, phrase) for phrase in rules.excluded):
        return False
    title_ok = any(_has(title, phrase) for phrase in rules.keywords)
    if not title_ok and rules.lower_level and _has(title, rules.lower_level):
        title_ok = _words(posting.get("company")).strip() in rules.lower_companies
    if not title_ok:
        return False
    if not rules.locations:
        return True
    location = posting.get("location") or ""
    if not location.strip() or posting.get("remote") or _is_remote(location):
        return True
    return any(_has(_words(location), place) for place in rules.locations)


# --- polling ----------------------------------------------------------------------------------


def _jobs(config: dict) -> list[tuple[str, str, str, object]]:
    """Every fetch to make: (key, url, kind, extra)."""
    jobs = []
    for kind, template in ENDPOINTS.items():
        for board in (config.get("boards") or {}).get(kind) or []:
            token = board["token"]
            company = board.get("company") or token
            jobs.append((f"{kind}:{token}", template.format(token=token), kind, (token, company)))
    aggregators = config.get("aggregators") or {}
    arbeitnow = aggregators.get("arbeitnow") or {}
    if arbeitnow.get("enabled"):
        for page in range(1, int(arbeitnow.get("pages", 1)) + 1):
            jobs.append((f"arbeitnow:page-{page}", ARBEITNOW.format(page=page), "arbeitnow", None))
    jobicy = aggregators.get("jobicy") or {}
    if jobicy.get("enabled"):
        for n, query in enumerate(jobicy.get("queries") or [], start=1):
            jobs.append((f"jobicy:query-{n}", JOBICY.format(query=query), "jobicy", None))
    return jobs


def poll(config: dict, rules: Rules, fetch, workers: int = 8, timeout: float = 20) -> dict:
    def one(item):
        key, url, kind, extra = item
        try:
            status, payload = fetch(url, timeout)
        except Exception as exc:  # one broken board must not stop the run
            return key, {"status": "error", "error": str(exc)}, []
        if status == 404:
            return key, {"status": "dead", "http": 404}, []
        if status != 200 or payload is None:
            return key, {"status": "error", "http": status}, []
        try:
            if kind in NORMALIZERS:
                postings = NORMALIZERS[kind](extra[0], extra[1], payload)
            elif kind == "arbeitnow":
                postings = normalize_arbeitnow(payload)
            else:
                postings = normalize_jobicy(payload)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return key, {"status": "error", "error": f"unexpected response: {exc}"}, []
        kept = [p for p in postings if keep(p, rules)]
        return key, {"status": "ok", "jobs": len(postings), "kept": len(kept)}, kept

    boards, candidates = {}, []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for key, info, kept in pool.map(one, _jobs(config)):
            boards[key] = info
            candidates.extend(kept)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017 (runs on Python 3.9+)
        "boards": boards,
        "candidates": candidates,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument("--out", default="candidates.json", help="output file inside the folder")
    p.add_argument("--workers", type=int, default=8, help="boards fetched at the same time")
    p.add_argument("--timeout", type=float, default=20, help="seconds per request")
    args = p.parse_args(argv)
    try:
        root = resolve_in(Path(args.dir), ".")
        out = resolve_in(root, args.out)
        config = read_json(root / "search-config.json")
        profile = load(root / "profile.yaml")
    except (FolderError, ProfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {os_problem(exc, 'read')}", file=sys.stderr)
        return 1
    result = poll(config, Rules.from_profile(profile), fetch_json, args.workers, args.timeout)
    try:
        write_json(out, result)
    except FolderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    boards = result["boards"]
    by_status = {
        s: [k for k, v in boards.items() if v["status"] == s] for s in ("ok", "dead", "error")
    }
    seen = sum(v.get("jobs", 0) for v in boards.values())
    print(
        f"boards: {len(boards)} polled, {len(by_status['ok'])} ok, {len(by_status['dead'])} dead, "
        f"{len(by_status['error'])} errors; postings: {seen} seen, "
        f"{len(result['candidates'])} kept -> {out.name}"
    )
    if by_status["dead"]:
        print("dead: " + ", ".join(by_status["dead"]))
    if by_status["error"]:
        print("errors: " + ", ".join(by_status["error"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

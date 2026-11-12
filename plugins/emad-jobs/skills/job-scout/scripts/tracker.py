#!/usr/bin/env python3
"""Keep the job tracker (jobs.json) correct: dedup, add, archive, revive, seen, record, backup,
validate.

Commands (all take --dir, the job search folder; the default is the current folder):

  dedup     Compare candidates.json with the tracker. Writes dedup.json with three lists:
            new (never seen), relisted (a role the agent archived as expired that is live
            again with a changed title or publish date) and known (already tracked, or a
            duplicate inside this run). Prints counts only.
  add       Add new roles from a JSON file (one object or a list). Refuses duplicates and
            user-owned fields; writes nothing if any entry is refused.
  archive   Archive a role with status 'new' and record why (for example: expired).
  revive    Move a role the agent archived as expired back to 'new' (the relist rule).
  seen      Record that roles were verified live today (updates last_verified).
  record    Record what the user told you about a role: its channel, whether a human was in
            touch (yes, no, or auto to derive it from the history), or the path of a contact
            search report (outreach/...). Never changes the status, history or user fields.
  backup    Copy jobs.json, job-search.md and search-config.json into backups/.
  validate  Check the tracker against the schema in references/tracker.md. Problems fail;
            warnings (for example an unknown channel) are printed but do not fail.

Rules the commands enforce: the agent never changes a status the user set (applied,
in_process, rejected, or an archive the user made), and never writes `my_notes`. The tracker
is backed up before the first write of the day.

Example:
  python3 tracker.py --dir ~/job-search dedup
  python3 tracker.py --dir ~/job-search archive --id acme-staff-engineer --reason expired
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jobfiles import (
    CHANNELS,
    DATE_RE,
    STATUSES,
    FolderError,
    backup,
    derive_human_contact,
    detect_vendor,
    load_tracker,
    os_problem,
    read_json,
    resolve_in,
    save_tracker,
    today_iso,
    write_json,
)

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
LONG_NUMBER_RE = re.compile(r"(?<![0-9])[0-9]{6,}(?![0-9])")
# Query parameters that carry a job id; every other parameter is tracking and is dropped.
ID_PARAMS = ("gh_jid", "ashby_jid", "lever_id", "jobid", "job_id", "id")
REQUIRED = ("id", "title", "company", "url", "status", "first_seen", "notes", "my_notes", "history")
DATE_FIELDS = ("first_seen", "last_verified", "applied_date", "rejected_date", "published")
USER_FIELDS = ("my_notes", "hiring_manager", "applied_date", "rejected_date")


class TrackerError(ValueError):
    """A command was refused. Nothing was written."""


# --- matching keys ----------------------------------------------------------------------------


def normalize_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    keep = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() in ID_PARAMS]
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(keep), ""))


def job_ids(url: str) -> set[str]:
    """Job ids inside a URL: UUIDs, and runs of 6 or more digits (Greenhouse, Workday ids)."""
    text = url or ""
    ids = {m.lower() for m in UUID_RE.findall(text)}
    stripped = UUID_RE.sub(" ", text)
    ids |= set(LONG_NUMBER_RE.findall(stripped))
    return ids


def _words(text: str) -> str:
    text = re.sub(r"[^\w]+", " ", (text or "").lower())
    text = re.sub(r"\b(sr|snr)\b", "senior", text)
    return " ".join(text.split())


def title_key(company: str, title: str) -> str:
    return f"{_words(company)}|{_words(title)}"


def _last(entry: dict) -> dict:
    history = entry.get("history") or []
    return history[-1] if history else {}


def archived_as_expired_by_agent(entry: dict) -> bool:
    last = _last(entry)
    return (
        entry.get("status") == "archived"
        and last.get("status") == "archived"
        and last.get("by") == "agent"
        and last.get("reason") == "expired"
    )


# --- classify ---------------------------------------------------------------------------------


def posting_key(company: str, title: str, location: str) -> str:
    return f"{title_key(company, title)}|{_words(location)}"


def company_ids(company: str, url: str) -> set[str]:
    """Job ids from the URL, tied to the company: two companies can reuse one number."""
    return {f"{_words(company)}|{i}" for i in job_ids(url)}


def classify(candidates: list[dict], jobs: list[dict]) -> dict:
    """Sort candidates into new, relisted and known. See the module help for the meaning.

    An ATS posting matches a tracked role by URL, by job id at the same company, or by
    company, title and location (a re-post under a new id). The same title in another
    place is a separate opening. An aggregator lead has no reliable location, so it matches
    by company and title only.
    """
    by_url, by_id, by_full, by_title = {}, {}, {}, {}
    for entry in jobs:
        company, url = entry.get("company", ""), entry.get("url", "")
        by_url.setdefault(normalize_url(url), entry)
        for key in company_ids(company, url):
            by_id.setdefault(key, entry)
        title = entry.get("title", "")
        by_full.setdefault(posting_key(company, title, entry.get("location", "")), entry)
        by_title.setdefault(title_key(company, title), entry)

    result: dict[str, list] = {"new": [], "relisted": [], "known": []}
    seen_urls, seen_ids, seen_full, seen_titles = set(), set(), set(), set()
    # Company boards first, so an aggregator lead for the same role is the duplicate.
    ordered = sorted(candidates, key=lambda c: bool(c.get("lead")))
    for cand in ordered:
        company, lead = cand.get("company", ""), bool(cand.get("lead"))
        url = normalize_url(cand.get("url", ""))
        ids = company_ids(company, cand.get("url", ""))
        full = posting_key(company, cand.get("title", ""), cand.get("location", ""))
        tkey = title_key(company, cand.get("title", ""))

        match, how = by_url.get(url), "url"
        if match is None:
            match = next((by_id[i] for i in ids if i in by_id), None)
            how = "job_id"
        if match is not None:
            info = {"id": match.get("id"), "status": match.get("status"), "by": how}
            changed = _words(cand.get("title")) != _words(match.get("title")) or (
                bool(cand.get("published"))
                and bool(match.get("published"))
                and cand["published"] != match["published"]
            )
            if archived_as_expired_by_agent(match) and changed:
                result["relisted"].append({**cand, "match": info})
            else:
                result["known"].append({**cand, "match": info})
            continue
        match = by_title.get(tkey) if lead else by_full.get(full)
        if match is not None:
            info = {"id": match.get("id"), "status": match.get("status"), "by": "company_title"}
            result["known"].append({**cand, "match": info})
            continue
        duplicate = url in seen_urls or ids & seen_ids or full in seen_full
        if duplicate or (lead and tkey in seen_titles):
            result["known"].append(
                {**cand, "match": {"id": None, "status": None, "by": "candidate"}}
            )
            continue
        seen_urls.add(url)
        seen_ids |= ids
        seen_full.add(full)
        seen_titles.add(tkey)
        result["new"].append(cand)
    return result


# --- validate ---------------------------------------------------------------------------------


def validate(data: dict) -> list[str]:
    problems = []
    statuses = tuple((data.get("meta") or {}).get("statuses") or STATUSES)
    seen_ids, seen_urls = set(), set()
    for n, entry in enumerate(data.get("jobs", [])):
        where = f"jobs[{n}] ({entry.get('id', '?')})"
        for field in REQUIRED:
            if field not in entry:
                problems.append(f"{where}: missing field {field!r}")
        status = entry.get("status")
        if status not in statuses:
            problems.append(f"{where}: unknown status {status!r}")
        if entry.get("id") in seen_ids:
            problems.append(f"{where}: duplicate id")
        seen_ids.add(entry.get("id"))
        url = normalize_url(entry.get("url", ""))
        if url and url in seen_urls:
            problems.append(f"{where}: duplicate url {entry.get('url')}")
        seen_urls.add(url)
        for field in DATE_FIELDS:
            value = entry.get(field)
            if value is not None and not DATE_RE.match(str(value)):
                problems.append(f"{where}: {field} must be YYYY-MM-DD, got {value!r}")
        score = entry.get("score")
        if score is not None and not (isinstance(score, int) and 0 <= score <= 10):
            problems.append(f"{where}: score must be a whole number from 0 to 10, or null")
        if entry.get("human_contact") not in (True, False, None):
            problems.append(f"{where}: human_contact must be true, false or null")
        history = entry.get("history")
        if not isinstance(history, list) or not history:
            problems.append(f"{where}: history must be a non-empty list")
            continue
        for h in history:
            if not isinstance(h, dict) or "status" not in h or "date" not in h:
                problems.append(f"{where}: every history entry needs 'status' and 'date'")
                break
        if _last(entry).get("status") != status:
            last = _last(entry).get("status")
            problems.append(f"{where}: last history entry is {last!r}, status is {status!r}")
    return problems


def warnings(data: dict) -> list[str]:
    """Things to tell the user about that do not make the tracker unusable."""
    found = []
    for n, entry in enumerate(data.get("jobs", [])):
        channel = entry.get("channel")
        if channel is not None and channel not in CHANNELS:
            found.append(
                f"jobs[{n}] ({entry.get('id', '?')}): channel {channel!r} is not one of "
                f"{', '.join(CHANNELS)}. Ask the user which it was, then run "
                "`tracker.py record --id <id> --channel <channel>`"
            )
    return found


# --- writes -----------------------------------------------------------------------------------


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _words(text)).strip("-")[:70] or "role"


def _find(data: dict, job_id: str) -> dict:
    for entry in data["jobs"]:
        if entry.get("id") == job_id:
            return entry
    raise TrackerError(f"no role with id {job_id!r} in jobs.json")


def add(data: dict, entries: list[dict], today: str) -> list[dict]:
    refused = []
    for e in entries:
        missing = [f for f in ("title", "company", "url") if not e.get(f)]
        if missing:
            refused.append(f"{e.get('title', '?')}: missing {', '.join(missing)}")
        owned = [f for f in USER_FIELDS if e.get(f)]
        if owned:
            refused.append(f"{e.get('title')}: {', '.join(owned)} belong to the user")
        if e.get("status", "new") != "new":
            refused.append(f"{e.get('title')}: the agent adds roles as 'new' only")
    if refused:
        raise TrackerError("refused: " + "; ".join(refused))
    sorted_out = classify(entries, data["jobs"])
    dupes = sorted_out["known"] + sorted_out["relisted"]
    if dupes:
        names = "; ".join(f"{d['company']} {d['title']} ({d['match']['by']})" for d in dupes)
        raise TrackerError(f"already tracked or duplicated in this file: {names}")

    ids = {entry.get("id") for entry in data["jobs"]}
    added = []
    for e in entries:
        base = _slug(f"{e['company']} {e['title']}")
        new_id, n = base, 2
        while new_id in ids:
            new_id, n = f"{base}-{n}", n + 1
        ids.add(new_id)
        entry = {
            "id": new_id,
            "title": e["title"],
            "company": e["company"],
            "url": e["url"],
            "status": "new",
            "score": e.get("score"),
            "location": e.get("location", ""),
            "work_style": e.get("work_style", ""),
            "compensation": e.get("compensation", "Not listed"),
            "why": e.get("why", ""),
            "watch_out": e.get("watch_out", ""),
            "source": e.get("source", ""),
            "published": e.get("published"),
            "first_seen": today,
            "last_verified": today,
            "applied_date": None,
            "notes": e.get("notes", ""),
            "my_notes": "",
            "vendor": e.get("vendor") or detect_vendor(e["url"]),
            "channel": e.get("channel", "portal"),
            "human_contact": None,
            "hiring_manager": "",
            "resume": e.get("resume"),
            "history": [{"status": "new", "date": today, "by": "agent"}],
        }
        data["jobs"].append(entry)
        added.append(entry)
    return added


def archive(data: dict, job_id: str, reason: str, today: str) -> dict:
    entry = _find(data, job_id)
    if entry.get("status") != "new":
        raise TrackerError(
            f"{job_id} has status {entry.get('status')!r}; the agent archives only roles with "
            "status 'new'. Other statuses are set by the user, so leave them"
        )
    entry["status"] = "archived"
    entry["history"].append(
        {"status": "archived", "from": "new", "date": today, "by": "agent", "reason": reason}
    )
    return entry


def revive(data: dict, job_id: str, today: str, title=None, published=None, url=None) -> dict:
    entry = _find(data, job_id)
    if not archived_as_expired_by_agent(entry):
        raise TrackerError(
            f"{job_id} was not archived as expired by the agent; only those can be revived. "
            "Report it to the user instead"
        )
    detail = f"relisted: title was {entry.get('title')!r}; published was {entry.get('published')}"
    if title:
        entry["title"] = title
    if published:
        entry["published"] = published
    if url:
        entry["url"] = url
    entry["status"] = "new"
    entry["last_verified"] = today
    entry["history"].append(
        {
            "status": "new",
            "from": "archived",
            "date": today,
            "by": "agent",
            "reason": "relisted",
            "detail": detail,
        }
    )
    return entry


# --- command line -----------------------------------------------------------------------------


def record(root: Path, data: dict, job_id: str, channel=None, human=None, outreach=None) -> dict:
    """Record facts the user gave about a role. Status, history and user fields stay as they are."""
    if channel is None and human is None and outreach is None:
        raise TrackerError("nothing to record: pass --channel, --human-contact or --outreach")
    entry = _find(data, job_id)
    if channel is not None:
        if channel not in CHANNELS:
            raise TrackerError(f"unknown channel {channel!r}; use one of {', '.join(CHANNELS)}")
        entry["channel"] = channel
    if human == "auto":
        entry.pop("human_contact_by", None)
        entry["human_contact"] = derive_human_contact(entry)
    elif human is not None:
        entry["human_contact"] = human == "yes"
        entry["human_contact_by"] = "user"
    if outreach is not None:
        path = resolve_in(root, outreach)
        if not path.is_file():
            raise TrackerError(f"{outreach} does not exist; write the contact report first")
        entry["outreach"] = path.relative_to(root.resolve()).as_posix()
    return entry


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument("--today", help="override today's date, YYYY-MM-DD (for tests and reruns)")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dedup", help="sort candidates.json into new, relisted and known")
    d.add_argument("--candidates", default="candidates.json")
    d.add_argument("--out", default="dedup.json")
    a = sub.add_parser("add", help="add new roles from a JSON file")
    a.add_argument("--file", required=True)
    r = sub.add_parser("archive", help="archive a 'new' role, with a reason")
    r.add_argument("--id", required=True)
    r.add_argument("--reason", required=True, help="for example: expired, duplicate")
    v = sub.add_parser("revive", help="move a role archived as expired back to 'new'")
    v.add_argument("--id", required=True)
    v.add_argument("--title")
    v.add_argument("--published")
    v.add_argument("--url")
    s = sub.add_parser("seen", help="record that roles were verified live today")
    s.add_argument("--id", required=True, action="append")
    c = sub.add_parser("record", help="record a role's channel, human contact or contact report")
    c.add_argument("--id", required=True)
    c.add_argument("--channel", help=f"one of: {', '.join(CHANNELS)}")
    c.add_argument(
        "--human-contact",
        choices=("yes", "no", "auto"),
        help="yes or no as the user said; auto derives it from the history again",
    )
    c.add_argument("--outreach", help="path of the contact search report, inside the folder")
    sub.add_parser("backup", help="copy the tracker, log and config into backups/")
    sub.add_parser("validate", help="check jobs.json against the schema")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = resolve_in(Path(args.dir), ".")
        today = today_iso(args.today)
        if args.command == "backup":
            made = backup(root, today, always=True)
            print(f"backed up {len(made)} file(s) into {root / 'backups'}")
            return 0
        data = load_tracker(root)
        if args.command == "validate":
            problems, notes = validate(data), warnings(data)
            for problem in problems:
                print(problem, file=sys.stderr)
            for note in notes:
                print(f"warning: {note}", file=sys.stderr)
            print(f"{len(data['jobs'])} roles, {len(problems)} problem(s), {len(notes)} warning(s)")
            return 1 if problems else 0
        if args.command == "dedup":
            out = resolve_in(root, args.out)
            raw = read_json(resolve_in(root, args.candidates))
            cands = raw.get("candidates", []) if isinstance(raw, dict) else raw
            result = classify(cands, data["jobs"])
            write_json(out, result)
            print(
                f"new: {len(result['new'])}  relisted: {len(result['relisted'])}  "
                f"known: {len(result['known'])}  -> {out.name}"
            )
            return 0
        if args.command == "add":
            raw = read_json(resolve_in(root, args.file))
            entries = raw if isinstance(raw, list) else [raw]
            added = add(data, entries, today)
            save_tracker(root, data, today)
            for entry in added:
                print(f"added {entry['id']}")
            return 0
        if args.command == "archive":
            archive(data, args.id, args.reason, today)
        elif args.command == "revive":
            revive(data, args.id, today, args.title, args.published, args.url)
        elif args.command == "record":
            record(root, data, args.id, args.channel, args.human_contact, args.outreach)
        elif args.command == "seen":
            for job_id in args.id:
                _find(data, job_id)["last_verified"] = today
        save_tracker(root, data, today)
        print(f"{args.command}: done")
        return 0
    except (TrackerError, FolderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {os_problem(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Report which hiring software (vendor) and channel each application went through.

Why: when many employers use the same screening software, one rejection can repeat
across all of them. This is called algorithmic monoculture. So many rejections through one
portal with no human ever in the loop are a signal to change the channel, not to send more
applications through the same portal.

Rule: a vendor with 3 or more rejections and no human contact on any application is
FLAGGED. If some rejections have human_contact still unknown (null), the flag is
PROVISIONAL until the user fills it in. A second table shows, per channel (portal,
referral, ...), how many applications reached a person.

A company careers page often hides the vendor on some postings and shows it on others (a
gh_jid parameter means Greenhouse). When all the known postings of a company share one
vendor, its 'company-own' postings are counted under that vendor; --fill writes it down
with vendor_inferred: true.

Usage:
  python3 vendor_report.py --dir ~/job-search                       # print the report
  python3 vendor_report.py --dir ~/job-search --out vendor-report.md
  python3 vendor_report.py --dir ~/job-search --fill   # add missing fields, infer vendors
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jobfiles import (
    CHANNELS,
    FolderError,
    derive_human_contact,
    detect_vendor,
    load_tracker,
    resolve_in,
    save_tracker,
    today_iso,
    write_text,
)

# Does the vendor score candidates itself, or mostly route applications to people?
VENDOR_CLASS = {
    "Workday": "scoring",
    "Eightfold": "scoring",
    "HireVue": "scoring",
    "iCIMS": "scoring",
    "Greenhouse": "routing",
    "Ashby": "routing",
    "Lever": "routing",
    "SmartRecruiters": "routing",
    "Recruitee": "routing",
    "Workable": "routing",
    "Personio": "routing",
}
APPLIED = ("applied", "in_process", "rejected")
NOT_KNOWN = ("company-own", "unknown", None, "")
SOURCE = (
    'Source: Stanford HAI (Institute for Human-Centered AI), May 2026, "AI Hiring Tools Can '
    'Yield Racial Bias and Systemic Rejection": '
    "https://hai.stanford.edu/news/ai-hiring-tools-can-yield-racial-bias-and-systemic-rejection"
)


def _company(job: dict) -> str:
    return " ".join(str(job.get("company") or "").lower().split())


def company_vendors(jobs: list[dict]) -> dict[str, str]:
    """Companies whose known postings all use one vendor, mapped to that vendor."""
    seen: dict[str, set] = {}
    for j in jobs:
        vendor = j.get("vendor") or detect_vendor(j.get("url"))
        if vendor not in NOT_KNOWN:
            seen.setdefault(_company(j), set()).add(vendor)
    return {company: next(iter(v)) for company, v in seen.items() if len(v) == 1}


def vendor_of(job: dict, known: dict[str, str]) -> str:
    vendor = job.get("vendor") or detect_vendor(job.get("url"))
    if vendor == "company-own" and _company(job) in known:
        return known[_company(job)]
    return vendor


def _human(job: dict):
    value = job.get("human_contact")
    return derive_human_contact(job) if value is None else value


def report(jobs: list[dict]) -> str:
    apps = [j for j in jobs if j.get("status") in APPLIED]
    known = company_vendors(jobs)
    stats: dict[str, dict] = {}
    by_channel: dict[str, dict] = {}
    for j in apps:
        human = _human(j)
        c = by_channel.setdefault(
            j.get("channel") or "portal", {"apps": 0, "human": 0, "rej_no": 0, "rej_unknown": 0}
        )
        c["apps"] += 1
        c["human"] += human is True
        if j.get("status") == "rejected":
            c["rej_no"] += human is False
            c["rej_unknown"] += human is None
        vendor = vendor_of(j, known)
        s = stats.setdefault(
            vendor, {"apps": 0, "rej": 0, "rej_no": 0, "rej_unknown": 0, "human": 0, "co": set()}
        )
        s["apps"] += 1
        s["co"].add(j.get("company", "?"))
        s["human"] += human is True
        if j.get("status") == "rejected":
            s["rej"] += 1
            s["rej_no"] += human is False
            s["rej_unknown"] += human is None

    lines = [
        "# Vendor report",
        "",
        f"Applications counted: {len(apps)} (status applied, in_process or rejected).",
        "",
        "| Vendor | Class | Apps | Rejections | Rejected, no human contact "
        "| Rejected, human contact unknown | Flag |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    flagged, provisional = [], []
    for vendor, s in sorted(stats.items(), key=lambda kv: (-kv[1]["rej"], -kv[1]["apps"], kv[0])):
        cls = VENDOR_CLASS.get(vendor, "unknown")
        flag = "ok"
        if s["rej"] >= 3 and s["human"] == 0:
            if s["rej_unknown"] == 0:
                flag = "**FLAGGED**"
                flagged.append((vendor, s, cls))
            else:
                flag = "PROVISIONAL: set human_contact to confirm"
                provisional.append((vendor, s, cls))
        lines.append(
            f"| {vendor} | {cls} | {s['apps']} | {s['rej']} | {s['rej_no']} | "
            f"{s['rej_unknown']} | {flag} |"
        )
    lines.append("")
    if flagged:
        lines += ["## Flagged: change the channel for these companies", ""]
        for vendor, s, cls in flagged:
            lines.append(
                f"- **{vendor}** ({cls}): {s['rej']} rejections, no human contact. "
                f"Companies: {', '.join(sorted(s['co']))}."
            )
        lines += [
            "",
            "Try a referral, a direct note to the hiring manager, or a community channel. "
            "The `hiring-contact-finder` skill finds the person behind a role and drafts the "
            "note. Apply through the portal as well: the hiring manager usually needs it.",
            "",
        ]
    if provisional:
        lines += ["## Provisional: the threshold is met, but the evidence is incomplete", ""]
        for vendor, s, cls in provisional:
            lines.append(
                f"- **{vendor}** ({cls}): {s['rej']} rejections, {s['rej_unknown']} with "
                "human_contact unknown. Fill it in from your inbox to confirm."
            )
        lines.append("")
    lines += [
        "## By channel",
        "",
        "| Channel | Apps | Reached a person | Rejected, no human contact "
        "| Rejected, human contact unknown |",
        "|---|---:|---:|---:|---:|",
    ]
    order = [c for c in CHANNELS if c in by_channel]
    order += sorted(c for c in by_channel if c not in CHANNELS)
    for channel in order:
        c = by_channel[channel]
        label = channel if channel in CHANNELS else f"{channel} (not a known channel)"
        lines.append(
            f"| {label} | {c['apps']} | {c['human']} | {c['rej_no']} | {c['rej_unknown']} |"
        )
    lines += [
        "",
        "A channel that reaches people where the portal does not is where the next "
        "applications should go.",
        "",
        "## How to read the Class column",
        "",
        "- **scoring**: the software ranks or tests candidates itself. Shared rejections across "
        "employers are most likely here, so a flag is a strong signal.",
        "- **routing**: the software stores applications and the employer's recruiters screen "
        "them. A flag more likely shows where your target companies post than a shared verdict.",
        "",
        SOURCE,
    ]
    return "\n".join(lines) + "\n"


def fill(jobs: list[dict]) -> int:
    """Add vendor, channel and human_contact where missing, and infer hidden vendors.

    A value is never overwritten, except 'company-own' when every known posting of that
    company uses one vendor (then vendor_inferred is set to true).
    """
    changed = 0
    for j in jobs:
        if "vendor" not in j:
            j["vendor"] = detect_vendor(j.get("url"))
            changed += 1
        if "channel" not in j:
            j["channel"] = "portal"
            changed += 1
        if "human_contact" not in j:
            j["human_contact"] = derive_human_contact(j)
            changed += 1
    known = company_vendors(jobs)
    for j in jobs:
        if j.get("vendor") == "company-own" and _company(j) in known:
            j["vendor"] = known[_company(j)]
            j["vendor_inferred"] = True
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument("--out", help="also write the report to this file inside the folder")
    p.add_argument(
        "--fill", action="store_true", help="add missing vendor/channel fields, infer vendors"
    )
    p.add_argument("--today", help="override today's date, YYYY-MM-DD")
    args = p.parse_args(argv)
    try:
        root = resolve_in(Path(args.dir), ".")
        data = load_tracker(root)
        if args.fill:
            changed = fill(data["jobs"])
            if changed:
                save_tracker(root, data, today_iso(args.today))
            print(f"filled {changed} missing field(s)")
            return 0
        text = report(data["jobs"])
        if args.out:
            write_text(resolve_in(root, args.out), text)
        print(text)
        return 0
    except FolderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

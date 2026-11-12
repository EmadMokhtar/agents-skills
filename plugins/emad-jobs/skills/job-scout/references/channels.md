# Channels and vendors

Finding roles is often not the hard part. Getting a human to read the application is. Track
**how** each application went in, and whether a person was ever involved, so the person can
see which channels work.

## Fields on every role

| Field | Values | Owner | Meaning |
| --- | --- | --- | --- |
| `vendor` | Ashby, Greenhouse, Lever, Workday, iCIMS, ..., `company-own`, `unknown` | agent | The hiring software (the platform) behind the posting. Found from the URL; a `gh_jid` parameter on a company page means Greenhouse. |
| `vendor_inferred` | `true` or absent | agent | The vendor was taken from the company's other postings (see below). |
| `channel` | `portal`, `referral`, `hiring-manager-direct`, `recruiter-inbound`, `community` | person | How the application went in. Default `portal`. |
| `human_contact` | `true`, `false`, `null` | both | Whether a person was ever involved. See below. |
| `human_contact_by` | `user` or absent | person | `user` means the person answered the question themselves. |
| `outreach` | a path | agent | The contact search report for this role ([outreach.md](outreach.md)). |

### human_contact

- `true` once the role reached `in_process`. This always wins.
- Otherwise, the person's own answer when `human_contact_by` is `user`. A named recruiter
  can write, call or interview without the card ever moving to In Process.
- Otherwise `null` (unknown), also after a rejection. A rejection alone does not show that
  no person was involved, so only the person can set `false`. Ask them after a rejection.

### Inferred vendors

A company careers page often hides the vendor on some postings and shows it on others. For
example, one URL has `gh_jid=` (Greenhouse) and the next does not. When every known posting
of a company uses one vendor, the vendor report counts that company's `company-own` postings
under it. `vendor_report.py --fill` writes it down, with `vendor_inferred: true`. A company
with two known vendors is left as it is.

## Recording what the person tells you

The person sets `channel` and their answer on human contact on the kanban board (open a
card, then Save). When they tell you instead, record it with `tracker.py`:

| The person says | Run |
| --- | --- |
| "An engineer at Acme referred me." | `tracker.py record --id <id> --channel referral` |
| "I wrote to the hiring manager, then applied." | `tracker.py record --id <id> --channel hiring-manager-direct` |
| "Their recruiter found me." | `tracker.py record --id <id> --channel recruiter-inbound` |
| "A recruiter called me" (the card is still Applied) | `tracker.py record --id <id> --human-contact yes` |
| "No one ever wrote back, only the system." | `tracker.py record --id <id> --human-contact no` |
| "I was wrong about that, use the history." | `tracker.py record --id <id> --human-contact auto` |

Record only what the person says. Never guess a channel or a human contact from anything
else. When more than one channel was used, record the one that is not the portal: the
report measures whether that extra step reached a person.

`tracker.py validate` warns about a `channel` value that is not in the list (for example an
older tracker's `direct`). Ask the person which channel it was, then record it.

## The vendor report

```bash
python3 <skill dir>/scripts/vendor_report.py --dir <folder> --fill
python3 <skill dir>/scripts/vendor_report.py --dir <folder> --out vendor-report.md
```

It counts applications (status `applied`, `in_process`, `rejected`) in two tables:

- **Per vendor.** A vendor with **3 or more rejections and no human contact** on any
  application is **flagged**. When some of those rejections have `human_contact` still
  unknown, the flag is provisional: ask the person to fill it in from their inbox.
- **Per channel.** How many applications went in through each channel, how many reached a
  person, and how many were rejected with no human contact. This is how the person sees
  that, for example, referrals reach people and the portal does not.

Why it matters: when many employers use the same screening software, a rejection by one
can repeat across all of them. This is called **algorithmic monoculture**. So ten
rejections through one portal may be one verdict, repeated. Vendors that **score**
candidates themselves (Workday, iCIMS, Eightfold, HireVue) make this more likely than
vendors that mostly **route** applications to the employer's recruiters (Greenhouse,
Ashby, Lever). Source: Stanford HAI (Institute for Human-Centered AI), May 2026,
[AI Hiring Tools Can Yield Racial Bias and Systemic Rejection](https://hai.stanford.edu/news/ai-hiring-tools-can-yield-racial-bias-and-systemic-rejection).

## What to suggest

When a vendor is flagged, or the person has many rejections with no human contact, suggest
another channel for the next roles at those companies. [outreach.md](outreach.md) has how,
with drafts:

- **Referral**: one engineer on or near the team.
- **Hiring manager direct**: a short note to the person who owns the role. The
  `hiring-contact-finder` skill finds that person from public, professional sources and
  drafts the note for the person to send.
- **Community**: channels where hiring engineers post themselves (see `channel_platforms`
  in `search-config.json`), or a meetup, a conference talk, an open-source project.

After a fast rejection with no human involved at an EU, EEA or UK employer, the person may
also ask for a human review of the decision. See [outreach.md](outreach.md).

Always add: apply through the portal **as well**. The hiring manager usually needs the
application in the ATS (applicant tracking system, the hiring software) to move the person
forward. Never send anything for the person.

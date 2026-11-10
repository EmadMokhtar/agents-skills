# Channels and vendors

Finding roles is often not the hard part. Getting a human to read the application is. Track
**how** each application went in, so the person can see which channels work.

## Fields on every role

| Field | Values | Meaning |
| --- | --- | --- |
| `vendor` | Ashby, Greenhouse, Lever, Workday, iCIMS, ..., `company-own`, `unknown` | The hiring software behind the posting. Found from the URL; a `gh_jid` parameter on a company page means Greenhouse. |
| `channel` | `portal`, `referral`, `hiring-manager-direct`, `recruiter-inbound`, `community` | How the application went in. Default `portal`; the person changes it. |
| `human_contact` | `true`, `false`, `null` | `true` once the role reached `in_process`; `false` when it was rejected without reaching `in_process`; otherwise unknown. |

`vendor_report.py --fill` adds missing fields without overwriting any value.

## The vendor report

```bash
python3 <skill dir>/scripts/vendor_report.py --dir <folder> --out vendor-report.md
```

It counts applications (status `applied`, `in_process`, `rejected`) per vendor. A vendor
with **3 or more rejections and no human contact** on any application is **flagged**. When
some of those rejections have `human_contact` still unknown, the flag is provisional: ask
the person to fill it in from their inbox.

Why it matters: when many employers use the same screening software, a rejection by one
can repeat across all of them (this is called algorithmic monoculture). So ten rejections
through one portal may be one verdict, repeated. Vendors that **score** candidates
themselves (Workday, iCIMS, Eightfold, HireVue) make this more likely than vendors that
mostly **route** applications to the employer's recruiters (Greenhouse, Ashby, Lever).

## What to suggest

When a vendor is flagged, or the person has many rejections with no human contact, suggest
another channel for the next roles at those companies:

- **Referral**: someone the person knows at the company.
- **Hiring manager direct**: a short note to the person who owns the role. The
  `hiring-contact-finder` skill finds that person from public, professional sources and
  drafts the note for the person to send.
- **Community**: channels where hiring engineers post themselves (see `channel_platforms`
  in `search-config.json`), or a meetup, a conference talk, an open-source project.

Always add: apply through the portal **as well**. The hiring manager usually needs the
application in the ATS to move the person forward. Never send anything for the person.

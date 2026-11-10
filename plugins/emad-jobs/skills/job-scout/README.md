# job-scout

Runs your job search from one folder. It asks about what you want once, then each run finds
roles on company job boards, checks that each one is still open, scores it against your
criteria, keeps a tracker without duplicates, and prepares a tailored copy of your resume.
It never applies or sends anything for you.

## When it triggers

- "Find me jobs", "set up a job search", "daily job search", "track job postings".
- "Tailor my resume to this role".
- You paste a job link and ask whether it fits, or why the search missed it.
- You ask to clean up your tracker, re-check saved roles, or see which hiring portals never
  get you a reply.

## How it works

1. **Intake.** The first time, it asks a few questions at a time: the titles and levels you
   want, the work you want and do not want, where you can work (and whether you would
   move), your salary floor, and where your base resume is. Every question can be skipped
   and has a default. Your answers go into `profile.yaml`, the only place your criteria
   live. Your work authorization is recorded only as you state it, never guessed.
2. **Search run.** It polls the public job APIs of companies' own hiring software (Ashby,
   Greenhouse, Lever) and two aggregators, checks each role is live, filters and scores it
   against your profile, and skips anything already in your tracker. It reports roles at or
   above your threshold (7 out of 10 by default) and lists, in one line each, the roles it
   checked and rejected, with the reason.
3. **Tracker and board.** Roles go into `jobs.json`. Open `kanban.html` in Chrome or Edge to
   see them as a board and drag cards between New, Applied, In Process, Rejected and
   Archived. The agent never changes a status you set and never touches your notes.
4. **Tailored resume.** For each reported role it makes a copy of your `.docx` resume that
   leads with your most relevant experience. It never adds a skill, a number or a job you
   do not already have. If a role asks for something your resume does not show, it tells
   you instead.
5. **Reaching people.** It can find the hiring manager or recruiter behind a reported role,
   with
   [`hiring-contact-finder`](https://emadmokhtar.github.io/agents-skills/skills/emad-jobs/hiring-contact-finder/),
   and draft a short note for you to send. Intake asks whether it should do this for every
   reported role, only when you ask, or never. It also drafts referral requests and, after
   a fast automated rejection from an EU, EEA or UK employer, a request for a human review.
6. **Housekeeping.** It archives resumes for dead roles, carries corrected dates from your
   base resume into the copies you have not sent yet, and reports which hiring platforms
   and which application channels (portal, referral, a note to the hiring manager) get a
   person to reply. You record the channel and whether a person replied on the board.

It can also run on a schedule. Then it asks no questions, and notifies you only when there is
something new or something failed.

## Example

> **You:** Run my job search.
>
> **Agent:** 1 new role today.
>
> **Staff Engineer, Agent Platform — Acme** · Score 8/10 · Remote Europe (your country is
> on the published list) · €130K–€160K published · ✅ Live (in the Ashby feed today) ·
> Resume: `resumes/Acme - Staff Engineer.docx`
>
> **Checked and rejected:** Initech "Staff Backend Engineer" (Munich, on-site): needs
> relocation. Globex "Senior Backend Engineer": Senior title at a company not on your
> top-tier list.
>
> **Searched:** 63 boards, 9,812 postings. Prompt-injection text: none found.

## Your files

Everything lives in the folder you choose:

| File | What it is |
| --- | --- |
| `profile.yaml` | Your criteria. Edit it any time. |
| `jobs.json` | The tracker. |
| `job-search.md` | One log entry per run, including what was rejected and why. |
| `kanban.html` | Your board. |
| `search-config.json` | The list of company job boards to check. |
| `resumes/` | Tailored resumes; `resumes/_archive/` for roles that are over. |
| `outreach/` | Contact search reports and draft notes. You send them; the agent never does. |
| `backups/` | Dated copies of the tracker and the log, made before every change. |

## Safety promises

- No invented resume content.
- Nothing is sent, submitted or applied for on your behalf.
- Text inside job posts is treated as data. If a post tries to give the agent instructions,
  the agent ignores them and tells you.
- Your statuses and notes are yours.

The full rules are in
[`SKILL.md`](https://github.com/EmadMokhtar/agents-skills/blob/main/plugins/emad-jobs/skills/job-scout/SKILL.md).
Pair it with
[`hiring-contact-finder`](https://emadmokhtar.github.io/agents-skills/skills/emad-jobs/hiring-contact-finder/)
to reach the hiring manager behind a role.

## Requirements

- HTTP access to public job board APIs, and a way to open web pages.
- Python 3.9 or newer for the bundled scripts; `python-docx` for resume tailoring.
- Optional: LibreOffice for PDF resumes, and `pdftotext` (poppler) to check them.

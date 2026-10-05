---
name: hiring-contact-finder
description: Finds the hiring manager or recruiter behind a job posting from public, professional sources (not LinkedIn), picks the best professional contact channel, and drafts a short, genuine outreach message for the candidate to review and send. Use whenever someone shares a job URL (Ashby, Greenhouse, Lever, Workable, a careers page) and wants to reach a real person, find who is hiring, contact the hiring manager or recruiter, get past an automated ATS screen, write a cold message about a role, or ask "who should I email about this job?" — even if they do not use the words "hiring manager". Optional input is the candidate's resume or background.
license: MIT
compatibility: Needs web search and the ability to fetch public web pages. Works with any agent that supports the Agent Skills format. No scripts or packages required.
metadata:
  author: Emad Mokhtar
---

# Hiring Contact Finder

Help a candidate reach a real person about a job they care about. The output is a
short research report plus a draft message. The candidate reads it, decides, and
sends the message themselves.

Why this exists: many hiring platforms filter applications automatically. A short,
specific note to the person who owns the role makes a human look at the candidate.
It works best **together with** a normal application, not instead of one. The
hiring manager usually needs the application in the ATS (applicant tracking
system — the hiring software) to move the candidate forward.

## Inputs

- **Job URL** (required).
- **Resume or background** (optional). It can be a file, pasted text, or what you
  already know about the user. If there is nothing, ask once for 2–3 lines about
  their experience, and do the research while you wait. If the user does not give
  them, or asks you to go ahead without them, continue: report the fit as **Not
  checked** (step 2) and write the draft with clear placeholders (step 5).

## Privacy rules (read before searching)

This skill looks up real people. Treat them the way a thoughtful professional
would. A recruiter who feels watched will not reply, so these rules also protect
the candidate. Read [references/privacy-rules.md](references/privacy-rules.md)
for the full list and the reasons. The short version:

- Use only **public, professional** information about a person: name, job title,
  team, and things they published in a work context.
- Use only **professional channels**: a contact the person published, a public
  work channel, a public professional post, or a work email.
- Do **not** look for or report personal phone numbers, home addresses, personal
  email addresses, family details, or private or personal social accounts.
- Do **not** use LinkedIn, people-search sites, data brokers, or leaked data.
- Collect only what is needed to send one message about this job.
- A guessed email address is always labelled **unverified**.

## Workflow

### 1. Read the job post

Fetch the job URL. Extract: company, job title, team or department, location and
remote policy, seniority, key requirements, posting date, and any person named on
the page (some Ashby and Greenhouse pages name the recruiter or hiring manager).

Many ATS pages are built with JavaScript, so a plain page fetch may return only
the title. If that happens, use the ATS's public JSON API (a machine-readable
version of the job data) or search for the exact job title on job aggregator
sites. [references/sources-and-channels.md](references/sources-and-channels.md)
lists the API address for each ATS. These APIs can miss unlisted roles. A page that
loads does not prove the role is open: closed postings often stay reachable. Report
"open (unlisted)" only when the role is missing from the API and its page still
shows a working way to apply (an apply button or form). If you cannot tell whether
applications are still accepted, report "unclear".

If the role is clearly closed, say so and stop. Searching for contacts for a
closed role wastes everyone's time.

### 2. Check the fit

Compare the requirements with the candidate's background. Give a short verdict:
**Strong**, **Partial**, or **Weak**, with 2–4 reasons. List the strongest
matching points. They become the core of the message.

Always check **location and work eligibility** too: the listed countries, the
remote policy, and relocation support. Compare them with where the candidate
lives. A location mismatch is often the biggest risk, and it is worth raising in
the message as a direct question.

Name the most important gap. If a key requirement is missing from the
candidate's background, say what concrete example would cover it.

If the fit is Weak, say so honestly and ask whether to continue. A message about a
poor fit uses up the candidate's one chance with that person.

If there is no background (see Inputs), do not guess a verdict. Report the fit as
**Not checked**, and still list the key requirements and the location rules so the
candidate can judge the fit themselves.

### 3. Find the people

The goal is the person who owns the hiring decision (usually the hiring manager —
the team lead or engineering manager the role reports to) and the recruiter for
the role. Search public sources in this order. See
[references/sources-and-channels.md](references/sources-and-channels.md) for
search patterns per source.

1. The job post itself and the company's careers page.
2. Public posts announcing this role: X, Bluesky, Mastodon, Threads, Hacker News
   "Who is hiring" threads, Reddit, company Slack or Discord communities, and
   newsletters.
3. The company's engineering blog, team pages, press releases, and open-source
   repositories (people who lead the team's projects).
4. Conference talks, podcasts, and meetup pages where team leads present.

Use several searches with different terms. One search is rarely enough. Prefer
recent sources, because people change teams.

For each person, record: name, role, how they relate to this job, evidence (a
link and one line on what it shows), and a confidence level:

- **High** — they posted or are named for this exact role, or they clearly lead
  the team the role is in.
- **Medium** — they lead a closely related team, or recruit for this department.
- **Low** — they work at the company in a relevant area, but the link to this
  role is a guess.

Report at most 3 people. Low-confidence people may appear in the table, but they
get no draft message. If you find no one with at least Medium confidence, say so.
Do not invent a person or a title.

Some situations come up often:

- **The team's manager role is also open** (for example a separate "Engineering
  Manager, <same team>" posting). Say so. The hiring decision probably sits higher
  up, so prefer the technical recruiter.
- **The role serves the whole engineering organisation** and has no named team.
  A VP or Head of Engineering is then a reasonable contact. Ask them to look at the
  application "or pass it to the person hiring".
- **Very senior people** (C-level, SVP) are not good contacts for a single role,
  unless they posted about the role themselves.
- **Same name, different organisation.** Product names and people's names often
  match unrelated companies or people. Confirm that the source really belongs to
  this company before you use it.
- **Undated sources.** Mark them "undated" in the evidence column. They lower
  confidence, because people change roles.

**Fallback when no one reaches Medium.** Use the channels that exist for this role:
the application's free-text or cover-letter field, if the form has one, and a reply
to the recruiter, if one contacts the candidate after they apply. Do not promise a
channel you have not seen. Suggest searching again in 1–2 weeks, because new teams
often announce hiring later.

### 4. Pick the contact channel

For each person, choose the best professional channel. Use this order of
preference and say why you picked it:

1. A contact the person published for this purpose (for example "DM me" or "email
   me at …" in the job post).
2. A reply or DM on the public post where they announced the job.
3. A public work contact: their professional website's contact form or listed work
   email, or a company page that lists them.
4. A company recruiting address (for example `jobs@` or `careers@`), with the
   person's name in the subject line.
5. A guessed work email built from the company's public email format. Show the
   evidence for the format and mark it **unverified**. Suggest the candidate
   confirms it from a first-party source (for example a page where the person
   published it) before sending. Do not suggest email-verification services: many
   of them probe mail servers, which the privacy rules forbid. The evidence bar: at least two published addresses of staff who are not
   founders. One founder's address is not enough, because founders often have
   special addresses. If the bar is not met, write "email format unknown" and do
   not guess. Do not list possible formats or example addresses for the person
   either: a list of options is a guess too.
6. The application's own free-text or cover-letter field, if the form has one.
   It reaches the people who own the role.

Never use a personal channel, even if you happen to see one.

Recommend contacting **one person first**. Name a second person only as a
backup, for use if the first channel fails. Two people at the same company who
get the same note at the same time will see it as mass messaging.

### 5. Draft the message

Read [references/outreach-message.md](references/outreach-message.md) before you
write. The message must be specific, short, honest, and in the candidate's voice.
Adjust the length to the channel: a DM is 3–5 sentences, an email is up to about
150 words. Write a draft for the first-choice person. Write a second draft only
for the backup person, and adapt it to what that person does.

If the candidate's background is missing (see Inputs), write the draft with clear
placeholders such as `[one concrete result from your work that matches X]`.

### 6. Report back

Use this structure in the chat:

```
## <Job title> at <Company>
Status: open / open (unlisted) / closed / unclear (posted <date>)
Apply link: <url>
Key facts: <team> · <location and remote policy> · <pay, if listed>

### Fit: Strong | Partial | Weak | Not checked
- <reason>
- <reason>
- Location: <eligible / risk / not eligible> — <why>
- Main gap: <gap and the example that would cover it>

### People
| Name | Role | Link to this job | Confidence | Evidence |
|---|---|---|---|---|

### Who to contact
- First choice: <Name> via <channel> — <why>. <"unverified" if guessed>
- Backup: <Name> via <channel> — <why> (only if the first channel fails)

### Draft message(s)
<channel label + subject line for email>
<message>

### Before you send
- [ ] Replace every [placeholder] with a real detail.
- [ ] Confirm any "unverified" address from a first-party source.
- [ ] Apply first, so "I applied today" is true.

### Next steps
1. Apply through the official link today (if not done yet).
2. Send the message within a day of applying.
3. If there is no reply after 7 working days, send one short follow-up. Then stop.

### Sources
- <title>: <url>
```

Keep the report short. Do not include anything about a person's private life.
Only include facts you found and can link to.

## Edge cases

- **Large companies** with many teams: find the specific team first (from the job
  title, the requirements, or the team name). Then search for that team's lead. A
  random engineering director is not useful.
- **Agency or anonymous posts:** say the employer is hidden. Suggest the agency's
  recruiter as the only contact.
- **Small startups:** the founder or CTO is often the hiring manager. A founder's
  public post about hiring is strong evidence.
- **Several open roles in one team:** mention in the message which role you mean,
  with the link.
- **A new internal project or incubator** (an internal startup inside a large
  company): the founding lead may not be hired yet, and there may be no public
  footprint. Say so. Rely on the application's free-text field and suggest
  searching again later.
- **The user asks for personal contact details or private information:** decline
  that part politely. Explain that it usually hurts the candidate's chances. Offer
  the professional channel instead.

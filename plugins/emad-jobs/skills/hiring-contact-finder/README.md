# hiring-contact-finder

Finds the hiring manager or recruiter behind a job posting, picks the best professional way
to reach them, and drafts a short message for you to review and send yourself.

Many hiring platforms filter applications automatically. A short, specific note to the
person who owns the role makes a human look at your application. It works best **together
with** a normal application, not instead of one.

## When it triggers

- You share a job link (Ashby, Greenhouse, Lever, Workable, or a careers page) and ask who
  is hiring.
- You ask how to reach the hiring manager or recruiter for a role.
- You ask for a short cold message about a role.

You can also give it your resume or a few lines about your experience. Without them, the
draft message uses clear `[placeholders]` instead of invented details.

## What you get

A short report in the chat:

- the role's status, key facts, and a link to apply;
- a fit verdict (**Strong**, **Partial** or **Weak**), including location and work
  eligibility, and the main gap;
- up to three people, each with their role, a confidence level and a linked source;
- one person to contact first, through one professional channel, and a backup;
- a draft message, a short "before you send" checklist, and the next steps.

You read it, decide, and send the message yourself.

## Privacy promises

The people it looks up did not ask to be researched, and outreach that feels invasive does
not get a reply. So the skill:

- uses only public, professional information: name, job title, team, and work they
  published;
- uses only professional channels: a contact the person published, a reply on their public
  post about the job, a work email, or the application form itself;
- never uses LinkedIn, people-search sites, data brokers or leaked data;
- never looks for personal phone numbers, home addresses, personal email addresses or
  private accounts, and declines politely if you ask;
- labels any guessed work email **unverified**, and guesses one only when at least two
  published addresses of staff (not founders) show the format.

The full rules are in
[`references/privacy-rules.md`](https://github.com/EmadMokhtar/agents-skills/blob/main/plugins/emad-jobs/skills/hiring-contact-finder/references/privacy-rules.md).

## Requirements

The agent needs web search and the ability to fetch public web pages. No scripts or
packages are needed.

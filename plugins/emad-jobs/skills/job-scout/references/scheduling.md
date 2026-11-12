# Running unattended

A scheduled run (cron, a scheduled agent task, a CI job) has no one to answer questions.
It must still follow every hard rule in SKILL.md.

## The scheduled prompt

Keep it short, and keep criteria **out** of it. Criteria live only in `profile.yaml`, so
the prompt and the profile can never disagree:

> Use the job-scout skill. Run the daily search in `<folder>`. This is an unattended run.

If an old prompt or note contains criteria that disagree with `profile.yaml`, follow the
profile and say so in the log.

## Rules for an unattended run

- **Folder mode only.** An unattended run needs a folder that stays: a coding agent or a
  desktop app with a connected folder ([environments.md](environments.md)). Start with
  `check_folder.py --dir <folder> --network`. If the folder cannot be used, stop and
  notify: "The job search could not run: <the FAIL line>."
- **Ask no questions.** When something is unclear, choose the safe option, state the
  assumption in the log ("Assumed: the Berlin office role needs relocation, so it was not
  added"), and continue.
- **No profile.yaml?** Do not search. Stop, and notify: "job-scout needs a profile first.
  Run intake in `<folder>`."
- Do every step of the run workflow, including housekeeping. Write the log entry even when
  nothing is new.
- **Contact search** follows `outreach.find_contacts`: with `ask` (the default), do not
  search, only list the roles it is available for; with `auto`, run it for at most
  `outreach.max_per_run` roles ([outreach.md](outreach.md)).
- **Never** apply, sign in, accept terms, or send a message. Prepare; the person acts.
- If a step fails (no network, a script error, an unreadable tracker), stop writing, keep
  the backups, and report the failure.

## Notifications

- With `search.notify_only_on_news: true` (the default), notify only when there is
  something new (a new or relisted role, an expired role the person applied to) or when the
  run **failed**. A quiet day writes the log and sends nothing.
- **Lead with the most important sentence**, so it is readable on a phone lock screen:
  "2 new roles: Acme Staff Engineer (8/10), Globex Tech Lead (7/10)." or "The job search
  failed: the tracker could not be read."
- Then one line per role, then the folder or log path. Keep the full report in the log, not
  in the notification.

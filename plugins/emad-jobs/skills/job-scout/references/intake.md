# Intake: build profile.yaml

Intake turns a conversation into `profile.yaml`. That file is the **only** place for the
person's criteria. Run intake when the folder has no `profile.yaml`, or when the person asks
to change their search.

## How to ask

- Ask **2 to 4 questions per turn**, one group at a time, in the order below.
- Every question can be skipped. Say what the default is, so "skip" is an easy answer. Record
  the default in the profile and list it in the summary at the end.
- Use the person's own words for titles, work and evidence. Do not "improve" them.
- If the person gives a resume first, read it and propose answers ("Your resume shows Go and
  Python; should `stack` be Go, Python, PostgreSQL?"). They confirm or correct. Never fill a
  field from the resume without asking.
- Do not ask about things a later group covers. Do not repeat a question that was answered.

## Group 1: role

1. Which job titles do you want? (`role.target_titles`; no default, ask again once if skipped)
2. Which levels count? For example Staff, Principal. (`role.levels`; default: the level in
   the titles)
3. Are there other titles that are the same level for you in some markets? For example,
   in some EU markets "Solution Architect" or "Tech Lead" is a Staff-level individual
   contributor role. (`role.equivalent_titles`; default: none). These pass only when the
   body passes `role.equivalent_titles_check` (default: hands-on IC scope, no people
   management, no sales quota or pre-sales).
4. Which titles should be dropped at once? (`role.excluded_titles`; default: none)

Then one follow-up: "Would you accept a lower title, for example Senior, at a short list of
top companies?" If yes, record `role.lower_title_exception`: the level, the exact company
names (`allowed_at`), and the person's test for "top company" (`test`). Default: no
exception.

## Group 2: work

1. What work do you want to do? (`work.wanted`)
2. What work do you not want? A role that is mainly this scores at most 6.
   (`work.unwanted`)
3. What kind of company? For example product company, AI-native, scale-up.
   (`work.company_types`)
4. Any industries to avoid? (`work.excluded_industries`; default: none). Also ask whether
   consultancies or agencies are acceptable (`work.allow_consultancies`; default: no).

Ask for the main technologies too (`work.stack`). A hard must-have outside the stack is a
watch-out on the role, not a reason to drop it.

## Group 3: location

1. Where do you live? (`location.home_base`)
2. Remote, hybrid, office: which are fine, and where can an office be?
   (`location.work_styles`, `location.office_areas`; default: remote and hybrid)
3. Would you move for a job? If yes, where? (`location.relocation`,
   `location.relocation_targets`; default: **no**)
4. What is your work authorization? Record it **exactly as the person states it**
   (`location.work_authorization`). Never infer it from a name, a nationality, a location or
   a resume. If the person skips it, leave it empty and write "work authorization: unknown"
   in reports.

Also ask which countries they can be employed from for remote roles
(`location.remote_countries`), their time zones, and the most travel they accept.

## Group 4: money and contract

1. What is your lowest acceptable yearly base salary, and in which currency?
   (`money.salary_floor`, `money.currency`; default: no floor)
2. Permanent, contract, or both? (`money.employment_types`; default: permanent)
3. Fewest hours per week? (`money.min_hours_per_week`; default: 32)

## Group 5: search

1. Which companies should every run check? (`search.priority_companies`). For each one, find
   its board token now (see [sources.md](sources.md)) and add it to `search-config.json`.
2. From what score out of 10 should a role be reported? (`search.report_threshold`;
   default: 7)
3. Should this run on a schedule? When? (`search.schedule`; default: by hand only)
4. On a schedule, notify only when there is something new? (`search.notify_only_on_news`;
   default: yes)

Offer the starter boards in `search-config.json` (`starter_boards`): copy only the ones the
person wants into `boards`.

## Group 6: resume

1. Where is your base resume (.docx)? (`resume.base_docx`). PDF-only resumes cannot be
   tailored: ask for the .docx.
2. Which parts may tailoring change? (`resume.editable_sections`; default: summary, skills,
   key bullets)
3. What is your strongest evidence to lead with? (`resume.lead_evidence`)

## Group 7: reaching people

Portals often reject people with no human ever reading the application. A short note to
the person who owns the role helps. Ask:

1. "When a role fits, should I also find its hiring manager or recruiter and draft a short
   note for you to send? I use the `hiring-contact-finder` skill for this. It uses only
   public, professional sources (not LinkedIn), and you always send the note yourself."
   (`outreach.find_contacts`: `ask` to offer it after each run, `auto` to do it for every
   reported role, or `never`; default: `ask`)
2. Only for `auto`: "At most how many roles per run?" Each search takes many web searches.
   (`outreach.max_per_run`; default: 3)

Check that `hiring-contact-finder` is available to you. It ships in the same plugin
(`emad-jobs`). If it is not installed, say so and record the answer anyway: runs then
report "contact search skipped: hiring-contact-finder is not installed".

## Build the search keywords

The board poller keeps a posting only when its title contains one of
`search.title_keywords`, and (if set) its location contains one of
`search.location_keywords`. Build them from the answers, and show them in the summary:

- `title_keywords`: every level and every equivalent title, as short phrases: `Staff`,
  `Principal`, `Tech Lead`, `Member of Technical Staff`, `Founding`. They match anywhere in
  the title, so "AI Staff Engineer" passes. Do **not** add the exception level (for example
  Senior) here: the poller lets it through only at the `allowed_at` companies.
- `location_keywords`: the home city and country, the office areas, the remote countries,
  and region words that cover them (`Europe`, `EMEA`). Remote and unknown locations always
  pass, because the body must be read for the real rules. Leave it empty to keep every
  location.

## Write and confirm

1. Copy `assets/profile.template.yaml` to `profile.yaml` in the folder and fill it in. Keep
   the comments. Set `created` and `updated` to today.
2. Check it: `python3 <skill dir>/scripts/profile_yaml.py <folder>/profile.yaml`.
3. Show a short summary, grouped like the questions, with every default marked
   "(default)". Ask: "Is this right? Anything to change before the first search?"
4. Only after the person confirms, offer the first run.

## Changing the profile later

When the person changes a criterion ("I am open to Berlin now"), edit `profile.yaml`, set
`updated`, and show the changed lines. Never keep a criterion anywhere else: not in a
scheduled prompt, not in `search-config.json`, not in a note. If an old note disagrees with
the profile, the profile wins, and say so.

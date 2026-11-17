# Criteria and scoring

Every rule here reads its values from `profile.yaml`. Nothing in this file is about one
person. Read the **body** of every posting before you score it: titles and location fields
mislead often.

## Order of checks

1. **Disqualifiers** (below). One hit: drop the role. If it was a near miss, list it in one
   line under "Checked and rejected".
2. **Title and level.**
3. **Location.**
4. **Score** the six dimensions, apply the caps, and compare with
   `search.report_threshold` (default 7).

## Profile fields: filter or score

| Profile field | Used as |
| --- | --- |
| `role.target_titles`, `role.levels` | title filter |
| `role.equivalent_titles` + `equivalent_titles_check` | title filter, then a content test on the body |
| `role.excluded_titles` | disqualifier |
| `role.lower_title_exception` | lets the lower title pass at `allowed_at` companies only |
| `work.wanted` | role fit score |
| `work.unwanted` | cap: a role that is mainly this scores at most 6 |
| `work.company_types` | company fit score |
| `work.excluded_industries` | disqualifier |
| `work.allow_consultancies` | disqualifier when false |
| `work.stack` | stack fit score; a hard must-have outside it is a watch-out |
| `location.*` | location filter and location fit score |
| `money.salary_floor`, `money.currency` | disqualifier when the published maximum is below the floor; otherwise compensation score |
| `money.employment_types`, `money.min_hours_per_week` | disqualifier, then employment type score |
| `search.priority_companies` | company fit bonus; never lifts a disqualifier |

## Disqualifiers

Drop the role when any of these is true:

- The title contains an excluded title.
- The industry is in `work.excluded_industries`. Judge the company's real business, not the
  team name: payments software for a casino is gambling.
- The employer is a **consultancy or agency** and `work.allow_consultancies` is false. This
  includes recruitment agencies posting for an unnamed client.
- The listing is on a **freelance marketplace**, or is hourly gig work, when the profile
  wants permanent employment.
- The role is **part-time below** `money.min_hours_per_week`.
- The employer **cannot be identified or verified**: "a stealth startup", "the company", or
  a name with no website or careers page. Unverifiable employers are a common scam pattern.
- An architect, field, solutions or forward-deployed title is really **pre-sales**. Red-flag
  words in the body: `quota`, `pipeline`, `MEDDPICC`, `pre-sales`, "partner with our sales
  team", "identify, qualify and close", "trusted advisor", travel above 20%. Apply this to
  every Architect and FDE title, not only "Solution Architect".
- The location fails (next section).
- The published salary range ends **below** `money.salary_floor` (same currency, or convert
  and say so). When no range is published, do not drop: add "confirm pay against the floor"
  to the watch-outs.

## Title and level

Keywords match **anywhere** in the title, never only at the start. Lessons from real misses:

| Title shape | What to do |
| --- | --- |
| Leading qualifier: "AI Staff Engineer", "GenAI Technical Lead" | Same as the plain title. |
| "Tech Lead", "Technical Lead" | Often a Staff-level IC title in Europe. Open it and check the body for people management before you treat it as equivalent. |
| "Staff / Senior", "Senior/Staff" | Judge on the **body**: if the body asks for "a Senior engineer", it is a Senior role. |
| "Staff / Lead", "Staff/Principal" | Staff or above: passes. |
| Levelled titles: "Senior II", "Senior Engineer 3" | Still the lower level. Apply the lower-title exception. |
| "Sr", "Snr" | The same as Senior. |
| "Member of Technical Staff", "Member of Engineering" | Frontier labs use these as Staff-equivalent titles with no level word. Read the qualifications: many are research seats (PhD, publications, model training). |
| "Founding Engineer", "Founding ML Engineer" | No level word. Judge the scope in the body (owns the stack, sets direction, hires). |
| A word that sounds right, for example "agent" | Read the body. "Agent" can mean a data-collection daemon, not AI agents. |

**Lower-title exception.** A lower title (for example Senior) passes only when the company
is on `role.lower_title_exception.allowed_at`, and the role passes the exception's `test`.
Say the reason in the report: "Senior title, accepted: Globex is on your top-tier list." At
any other company, reject it in one line: "Senior title at a company not on your top-tier
list." The exception lifts **only** the title gate. Every other filter still applies, and at
a mixed company only the team or product line that matches `work.wanted` counts.

## Location

- Decide where the person must **live**, not where they must travel. Travel within
  `location.max_travel_percent` is fine.
- A **hybrid or office role anchored outside** `location.office_areas` is a relocation role
  in practice, even with "2 days a week in the office".
- **Remote roles have allow-lists.** Many "Remote Europe" or "Remote EMEA" roles hire only in
  some countries (payroll or employer-of-record reasons). Read the body for the list on
  **every** remote role. Do not trust the ATS location field: a field that says
  "Remote: EMEA" can sit above a body that says "we hire in the UK, Czechia or Italy". The
  role passes only when a country in `location.remote_countries` is on the list, or the
  role is worldwide. If no list is published, say so in the watch-outs.
- **Relocation roles.** If `location.relocation` is false, never add a role that needs a
  move to the tracker, however good it is. List it in one line under "Checked and rejected"
  ("Acme Staff Engineer, Munich on-site: needs relocation"). If relocation is true, a move
  to a place in `relocation_targets` passes.
- **Work authorization.** Use only `location.work_authorization`, as the person stated it.
  If it is empty, write "work authorization: unknown" and never guess.

## Score

Give each dimension a score out of 10, then an overall score out of 10. The overall score
is your judgement, led by role fit and company fit. Show the dimensions only when asked;
show the reasons always.

| Dimension | 10 | 5 | 0 |
| --- | --- | --- | --- |
| Company fit | type in `company_types`, or a priority company | neutral | excluded type |
| Role fit | mainly `work.wanted` | half wanted work | mainly unwanted work |
| Location fit | office in `office_areas`, or remote with an allowed country confirmed | remote with no published list | needs relocation (when not allowed) |
| Stack fit | the person's stack | some overlap, gaps are nice-to-haves | a hard must-have outside the stack |
| Compensation | published, clearly above the floor | not published | published below the floor |
| Employment type | in `employment_types`, full hours | unclear | not accepted |

Caps and rules:

- A role that is **mainly unwanted work** scores at most **6**, whatever else is true.
- A role that fails the location filter scores **0** for location and is dropped.
- A hard stack gap is never hidden: report the role with an honest score and a clear
  watch-out ("needs extensive Java; your stack is Go and Python"). Do not drop it silently,
  and do not inflate the score.
- Report a role only at or above `search.report_threshold`. Roles one point below may go in
  "Checked and rejected" with the reason.

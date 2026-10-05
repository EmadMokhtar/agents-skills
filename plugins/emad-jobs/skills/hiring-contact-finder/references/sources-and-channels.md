# Sources and search patterns

Use these as starting points. Change the terms to match the company, the role,
and the team. Replace `<Company>`, `<role>`, and `<team>` with real values.

## 1. The job post and the ATS

ATS (applicant tracking system) pages often contain more than the visible text.

- **Ashby** (`jobs.ashbyhq.com/<company>/<id>`): the page lists the team or
  department and sometimes the location group. The board root
  `jobs.ashbyhq.com/<company>` shows the other open roles in the same team, which
  helps to identify the team.
- **Greenhouse** (`job-boards.greenhouse.io/<company>/jobs/<id>`, or the `.eu.`
  host): look for the department and office. Some posts name the recruiter at the
  bottom.
- **Lever** (`jobs.lever.co/<company>/<id>`): the team and commitment fields are at
  the top.
- **Workable, Personio, Teamtailor, Recruitee**: look for a "Department" field and
  for a named contact.

Also check the company's own careers page. It sometimes introduces the team and
its manager.

### Public ATS APIs (use when the page needs JavaScript)

These return the same public job data as JSON (a structured text format):

| ATS | Job list | One job |
|---|---|---|
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/<company>?includeCompensation=true` | find the job id in the list |
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/<company>/jobs?content=true` | `https://boards-api.greenhouse.io/v1/boards/<company>/jobs/<id>` (has `first_published`, the real posting date) |
| Lever | `https://api.lever.co/v0/postings/<company>?mode=json` | `https://api.lever.co/v0/postings/<company>/<id>` |

Notes:
- The lists can be incomplete. Unlisted roles do not appear, but their pages still
  load. Report such a role as "open (unlisted)".
- A summarised page can show a wrong date. Prefer the API's date field.
- If the API also fails, search for the exact job title on job aggregators (sites
  that copy job posts, such as startup.jobs or builtin). They often show the full
  text and the posting date.

## 2. Public posts about the role

Search for posts announcing the job. Useful queries:

- `"<Company>" "<role>" hiring`
- `"<Company>" "we're hiring" <team>`
- `"<Company>" "join my team"` or `"join our team"`
- `site:bsky.app "<Company>" hiring`
- `site:x.com "<Company>" "<role>"` or `site:twitter.com ...`
- `site:mastodon.social "<Company>" hiring` (and other large instances)
- `site:news.ycombinator.com "<Company>"` (look in the monthly "Who is hiring"
  thread; posters often write "email me at ...")
- `site:reddit.com "<Company>" hiring <role>`

A post in which someone writes "my team is hiring" is the strongest evidence that
they are the hiring manager.

Hacker News pages often block automated fetches (errors 419 or 429). Use the
public Algolia search API instead:
`https://hn.algolia.com/api/v1/search?query=<Company>&tags=comment` (add
`,story_<thread id>` to search inside one "Who is hiring" thread).

## Grey-zone sources

Some sources are not LinkedIn or data brokers, but they are close. Use them
carefully:

- **Org-chart aggregators** (for example TheOrg): use them only to find a name
  or a title. Then confirm it on a first-party source (the company's own site, a
  post by the person, a talk page). Cite the first-party source. If you cannot
  confirm it, keep the person at Low confidence and say the listing may be
  unverified.
- **Community forums:** read public posts. Do not collect profile data such as
  "last seen" times or activity history. That is tracking, not research.
- **Usernames:** do not link an anonymous username to a real person by guessing.
  Use only identities the person states themselves.
- **Always skip:** RocketReach, ContactOut, LeadIQ, Lead411, Apollo, ZoomInfo,
  Hunter-style "email finder" pages, and any people-search site. They often rank
  high in search results. Do not open them.

## 3. Company content

- Engineering blog: `"<Company>" engineering blog <team topic>`. Authors who
  describe the team's systems are often its leads.
- Team or "about" pages, leadership pages, and press releases about new teams or
  products.
- Open-source repositories under the company's GitHub or GitLab organisation:
  maintainers of the team's main project.
- Company community spaces (public forum, Discord, Slack) where staff post jobs.

## 4. Talks and media

- `"<Company>" <team topic> talk` or `conference`
- Conference speaker pages, meetup pages, podcast episode notes.

These sources show who leads a team. They also give a genuine detail to mention
in the message.

## Confirming the right person

Before you report someone, check:

- Is the source recent (ideally from the last 12 months)? People change roles.
- Does the team match the role's team, not just the same company?
- Is there a second source that agrees? Two weak signals together can make Medium
  confidence.

## Finding the company email format

Only if no better channel exists:

- Look for work emails the company itself published: press contacts, security
  contacts, conference speaker pages, open-source commit metadata on public
  projects, published papers.
- Common formats: `first@`, `first.last@`, `flast@`, `firstl@`.
- The evidence bar is at least two published addresses of staff who are not
  founders. Founders often have special short addresses, so one founder address
  proves nothing.
- If the target person's own work address appears in public commit metadata on a
  company repository, it counts as published in a work context. Give its date.
  Still mark it unverified if it is older than about a year.
- Show the evidence ("press page uses first.last@company.com") and label the result
  **unverified**. If the bar is not met, write "email format unknown".
- Do not probe mail servers or use paid contact databases to confirm the address.

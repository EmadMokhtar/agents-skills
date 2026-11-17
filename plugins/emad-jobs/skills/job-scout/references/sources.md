# Sources: where postings come from

Prefer a company's own **ATS board** (ATS: applicant tracking system, the hiring software a
company uses). Its public API lists only open roles, so a role returned there is live.
Aggregators are for **discovery**: every aggregator result is a lead to confirm on the
company's own board.

## ATS APIs (no key needed)

| ATS | Endpoint | Notes |
| --- | --- | --- |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true` | Title, location, `isRemote`, `workplaceType`, `publishedAt`, full description, and compensation when published. Tokens can be case-sensitive. |
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | No server-side filtering. `content` is HTML with escaped entities. Some boards are hosted at `job-boards.eu.greenhouse.io/{token}`; the API token is the same. |
| Lever | `https://api.lever.co/v0/postings/{token}?mode=json` | Works, but few AI-native companies use it. Poll known tokens; do not spend a run guessing Lever tokens. |

`scripts/poll_boards.py` polls all three for every token in `search-config.json`. Other ATS
boards also have public endpoints (Recruitee `https://{token}.recruitee.com/api/offers/`,
Workable `https://apply.workable.com/api/v1/widget/accounts/{token}`, SmartRecruiters
`https://api.smartrecruiters.com/v1/companies/{token}/postings`, Personio
`https://{token}.jobs.personio.de/xml`). The script does not poll them: open them by hand
for the companies that use them.

## Aggregators (leads only)

| Aggregator | Endpoint | Notes |
| --- | --- | --- |
| Arbeitnow | `https://www.arbeitnow.com/api/job-board-api?page=N` | Paginated, about 100 jobs a page, a `remote` flag. Good EU coverage. |
| Jobicy | `https://jobicy.com/api/v2/remote-jobs?count=50&industry=engineering` | Remote roles. Read `jobGeo` for the region. |

Tested and **not useful**: Remotive and RemoteOK (little senior content), The Muse (paid,
credit-based). Google for Jobs returned nothing from several EU
locales. Many job sites (for example hiring.cafe, Wellfound, Himalayas) block requests from
other sites: use them by hand in a browser to **discover companies**, then add each
company's own board token to the registry.

## The board registry

Board tokens **cannot be guessed** from company names. A company that trades under a brand
name can use a short, unrelated token, and a token that looks right can belong to another
company with a similar name. Check that the postings on a new token really are the
company's.

So keep a registry in `search-config.json` and use it on every run:

- `boards.ashby`, `boards.greenhouse`, `boards.lever`: lists of
  `{"token", "company", "added", "note"}`. Poll every entry on every run.
- When a **new company enters the tracker**, find its token in the same run (open its
  careers page and look at where "Apply" goes) and add it.
- A token that returns **404** is dead: the company moved ATS or renamed the board. Find the
  new token, or move the company to `unresolved` with its careers URL.
- `unresolved`: companies with a custom careers site. Open them by hand when they matter.
- When the person pastes a role the run missed, find the cause (board not polled, title
  keyword, location keyword, or correctly rejected), fix the registry or the profile, record
  it in `miss_log`, and tell the person the cause.

## Practical limits

- **CORS.** A browser `fetch()` to these APIs from another site's page is blocked (CORS:
  the browser rule that stops one site's scripts from reading another site's data). Open
  the API URL itself in the browser first, or call the API from a shell or script.
- **Keep printed output small.** A run can see thousands of postings. Store results in
  files (`candidates.json`, `dedup.json`) and print counts, not postings.
- **Web search** is a fallback for breadth, and its links are often stale. Verify every link
  it gives before reporting it (see [verification.md](verification.md)).

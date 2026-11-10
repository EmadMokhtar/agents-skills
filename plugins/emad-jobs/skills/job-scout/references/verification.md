# Verify that a role is live

Never report a role you have not verified **today**. A dead link wastes the person's time
and their trust in the run.

## The rule

- A role returned by the company's **ATS API today** (Ashby, Greenhouse, Lever) is live. The
  API lists only open roles.
- **Everything else must be opened and read**: aggregator leads, web search results, links
  the person pastes, company careers pages. Many sites return HTTP 200 for a removed job, so
  a status code proves nothing.

## Red flags: the role is gone

- The page says "Job not found", "no longer accepting applications", or similar.
- The page title is generic ("Careers at Acme") instead of the role title.
- The URL redirects to a generic careers page, or adds `?error=true`.
- The role is missing from the company's ATS feed, even though the board token works.
- An aggregator lead points to a posting that the company's own board does not list.

## Client-rendered boards

Some boards build the page in the browser with JavaScript, so a plain fetch shows an empty
page. Use their JSON endpoint instead, and read the fields that decide the role: `status`
(open or closed), job type (permanent, contract, freelance), budget or salary, and hours.

## Re-verify tracked roles

On every run, check each role with status `new`:

- Still in its ATS feed, or still readable: run `tracker.py seen --id <id>`.
- Gone (red flags above): run `tracker.py archive --id <id> --reason expired`, and report it
  under "Expired". Its resume is archived by housekeeping.

Never re-verify by changing a role the person moved (applied, in_process, rejected).

## In the report

Say how each role was verified, for example "✅ Live (in the Ashby feed today)" or
"✅ Live (page opened today and shows the role title)". If you could not verify a role, do
not report it as a match: list it under "Checked and rejected" as "could not verify".

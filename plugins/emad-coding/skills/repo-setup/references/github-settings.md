# One-time GitHub settings

These settings cannot be set from a file. The new `docs/contributing.md` lists them for the
repository, already filled in. Give the user the commands below for the ones that apply. **The
user runs them.** Do not run them yourself: they change the repository on GitHub, and a ruleset
or a secret is not something to create by surprise.

Replace `OWNER/REPO` and `main`. Every command needs the GitHub CLI (`gh`), signed in with a token that
may administer the repository.

Contents: [Merge settings](#merge-settings) · [Ruleset](#ruleset-for-the-default-branch) ·
[Secret](#release-token) · [Pages](#pages-docs-site) · [Label](#label-docs-gates) ·
[Security features](#security-features-security) · [Packages](#packages-container) ·
[Check the result](#check-the-result)

## Merge settings

Squash merging only, with the pull request title as the commit title, and merged branches
deleted. The title becomes the commit that commitizen reads.

```bash
gh repo edit OWNER/REPO --enable-squash-merge --enable-merge-commit=false \
  --enable-rebase-merge=false --delete-branch-on-merge --squash-merge-commit-message pr-title
```

## Ruleset for the default branch

A ruleset that requires a pull request, blocks deletion and force pushes, keeps history linear,
allows squash merges only, and requires the checks. Repository admins can bypass it, which is how
the release token pushes the bump commit. The number `15368` is the GitHub Actions app.

Save this as `ruleset.json`. Add one `context` entry for each required check of the installed
modules: `checks` and `pr-title` (base), `docs-updated` (docs-gates), `dependency-review` and
`scan-tree` (security), `build` and `scan` (container).

```json
{
  "name": "protect-default-branch",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }
  ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [
          { "context": "checks", "integration_id": 15368 },
          { "context": "pr-title", "integration_id": 15368 }
        ]
      }
    }
  ]
}
```

```bash
gh api repos/OWNER/REPO/rulesets --input ruleset.json
```

If the repository's release tool opens its release pull requests with `GITHUB_TOKEN`
(release-please does by default), those pull requests do not start `checks` or `pr-title`, so a
required check blocks them. Give the release tool a personal access token, or do not require
those checks.

A required check that has never run cannot be selected in the web page, so create the ruleset
after the first pull request has run the workflows, or use the command above.

## Release token (release)

Only with the `release` module. Create a fine-grained personal access token for this repository only, with *Contents* set to read
and write, from an account that may bypass the ruleset. Then store it. The command asks for the
value, so it never appears in a file or in chat.

```bash
gh secret set RELEASE_TOKEN --repo OWNER/REPO
```

## Pages (docs-site)

The first docs deploy fails until the source is *GitHub Actions*.

```bash
gh api -X POST repos/OWNER/REPO/pages -f build_type=workflow
```

## Label (docs-gates)

```bash
gh label create no-docs-needed --repo OWNER/REPO --color 0E8A16 \
  --description "This change needs no documentation change"
```

## Security features (security)

The dependency review check needs the dependency graph. Dependabot alerts and security updates
open pull requests for known vulnerabilities. Private vulnerability reporting is what
`SECURITY.md` points to.

```bash
gh api -X PUT repos/OWNER/REPO/vulnerability-alerts
gh api -X PUT repos/OWNER/REPO/automated-security-fixes
gh api -X PUT repos/OWNER/REPO/private-vulnerability-reporting
```

On a private repository, `dependency-review` also needs GitHub Advanced Security. Without it,
delete that job.

## Packages (container)

After the first release has pushed an image, open the new package under the repository's
*Packages*, link it to the repository, and make it public if the image should be public. This has
no stable command, so it is done on the web page.

## Check the result

```bash
gh api repos/OWNER/REPO/rulesets -q '.[].name'
gh repo view OWNER/REPO --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge
```

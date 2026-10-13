---
last_reviewed: __TODAY__
---

# 0004. Pin actions by SHA and start with no permissions

**Status:** Accepted
**Date:** __TODAY__

## Context

A GitHub Action runs inside our workflow, with our token. A tag such as `v4` can be moved to
different code after we reviewed it. This is a known way to attack many repositories at once. A
workflow that gets broad permissions by default makes the damage larger.

## Decision

- Every action is pinned by full commit SHA, with the version in a comment:
  `uses: actions/checkout@<sha>  # v7.0.1`. A commit SHA cannot be moved.
- Every workflow starts with `permissions: {}`. Each job asks only for the permissions it needs.
- Dependabot moves the SHA and the version comment together, one pull request a week, so the
  pins do not go stale.

## Alternatives considered

- **Pin by tag.** Easy to read, but the tag can change under us.
- **Pin by major version only (`@v4`).** The same problem, and it also changes without a review.
- **Vendor the actions into the repository.** Safe, but we then maintain the copies ourselves.

## Consequences

- A workflow change that uses a new action needs the SHA looked up once. After that, Dependabot
  does the work.
- A job that needs more than read access to the repository says so in the workflow, where a
  reviewer can see it.

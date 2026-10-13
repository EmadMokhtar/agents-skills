---
last_reviewed: __TODAY__
---

# 0002. Conventional Commits

**Status:** Accepted
**Date:** __TODAY__

## Context

We want a history that people and tools can read. A tool can only read it if every commit
message says what kind of change it is.

## Decision

Every commit message and every pull request title follows
[Conventional Commits](https://www.conventionalcommits.org/). A git hook checks commit
messages, and a workflow checks pull request titles. Pull requests are squash-merged, so the
title is the commit on `__BRANCH__`.
<!-- @if release -->

[commitizen](https://commitizen-tools.github.io/commitizen/) reads those commits, picks the next
version, writes `CHANGELOG.md`, tags the release, and the Release workflow publishes it. The
version is the newest git tag (`version_provider = "scm"`), so no file stores it and the set-up
works for any language.
<!-- @endif -->

## Alternatives considered

<!-- @if release -->
- **release-please.** It opens a release pull request, works for any language, and is strong for
  repositories with many packages. We chose commitizen because it needs no release pull request
  and no extra bot token, and because one tool also checks the commit messages.
- **semantic-release.** It needs a Node.js toolchain in a repository that may have none.
- **Versions by hand.** They drift from what changed, and a changelog nobody writes is a
  changelog nobody has.
<!-- @else -->
- **Free-form messages.** They are quick to write and impossible for a tool to read.
- **Checking only in review.** A reviewer forgets, and a hook does not.
<!-- @endif -->

## Consequences

- A badly named title silently hides a change from the release, so the title check is required.
<!-- @if release -->
- The Release workflow pushes a `bump:` commit to `__BRANCH__`. On a protected branch this needs a
  `RELEASE_TOKEN` from an account that may bypass the rules.
- Before 1.0.0 a breaking change raises the minor number, not the major number.
<!-- @endif -->

---
last_reviewed: __TODAY__
---

# 0003. One check recipe for CI and laptops

**Status:** Accepted
**Date:** __TODAY__

## Context

When a workflow repeats the commands that a developer runs by hand, the two lists drift apart.
Then a change passes on a laptop and fails in CI, or the reverse, and nobody knows which list is
right.

## Decision

`just check` is the one definition of "the checks". The CI workflow runs `just check` and
nothing else for the checks. A new check is a new recipe that `check` depends on.

## Alternatives considered

- **Commands written in the workflow.** They cannot be run locally in one step, and they drift.
- **A Makefile.** It does the same job, but `just` has clearer syntax, lists its recipes, and
  runs the same on every operating system we use.
- **A script.** It hides the list of checks inside code.

## Consequences

- A failure in CI can be reproduced with one command.
- Workflows stay short, and CI changes are mostly changes to the `justfile`.
- A check that needs something CI provides itself, such as the `lychee` program, is the one
  accepted exception. It runs in its own job, and this record should mention it.

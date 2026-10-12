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

`just check` is the one definition of "the checks". The `checks` job in CI runs `just check` and
nothing else. A new check is a new recipe that `check` depends on.

A few gates need GitHub or the network: they compare a pull request with its base branch, call a
GitHub service, or fetch a vulnerability database. They run in their own CI jobs and have their
own recipes, and the contributing guide lists them. They are the only exception.

## Alternatives considered

- **Commands written in the workflow.** They cannot be run locally in one step, and they drift.
- **A Makefile.** It does the same job, but `just` has clearer syntax, lists its recipes, and
  runs the same on every operating system we use.
- **A script.** It hides the list of checks inside code.

## Consequences

- A failure in CI can be reproduced with one command.
- Workflows stay short, and CI changes are mostly changes to the `justfile`.
- A green `just check` does not cover those gates, so the contributing guide names them and the
  recipe that runs each by hand.

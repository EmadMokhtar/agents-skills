---
last_reviewed: __TODAY__
---

# 0005. Run the repository's tools the same way everywhere

**Status:** Accepted
**Date:** __TODAY__

## Context

This repository has tools of its own: a workflow linter, a secret scanner, a file check, and more.
If each person installs them by hand, their versions differ, and a check passes on one laptop and
fails in CI. The tools should not force a language setup on the project either.

## Decision

<!-- @if uv -->
The tools are Python packages, pinned in `pyproject.toml` and `uv.lock`, and `uv` runs them. `just`
recipes call `uv run`, and CI does the same, so a laptop and CI use the same versions. Dependabot
updates the pins.
<!-- @else -->
Each tool is a program that each person installs, for example with Homebrew. `just doctor` lists
the ones that are missing and how to install them. `just` recipes call the tools directly. CI
installs the same tools at pinned versions in one file, `.github/actions/setup-tools/action.yml`, and
runs the same recipes. The git hooks are plain scripts in `.githooks/`, so this repository needs no
`uv`, no `pyproject.toml` and no lock file for its tools.
<!-- @endif -->

## Alternatives considered

<!-- @if uv -->
- **Install each tool by hand.** The versions drift, and a new contributor spends an afternoon.
- **Containers.** They need Docker on every machine and are slower for small tools.
<!-- @else -->
- **Install each tool by hand.** The versions drift, and a new contributor spends an afternoon.
- **`uv` or another Python package manager.** It would add a `pyproject.toml`, a lock file and a
  Python version to a project that is not written in Python.
- **Pinned container images.** The versions are exact on every machine, but every contributor
  then needs Docker, and a hook that starts a container is slow.
<!-- @endif -->

## Consequences

<!-- @if uv -->
- Every contributor needs `uv` and `just`.
- The lock file changes when a tool is updated, and the change is reviewed like code.
<!-- @else -->
- Every contributor installs `just` and a few small tools. `just install` says which.
- A laptop may run a newer version of a tool than CI does, because the versions are pinned only in
  CI. A check that passes on a laptop but fails in CI is usually this.
- Updating a tool in CI is a change to one file, and nothing proposes it automatically.
<!-- @endif -->

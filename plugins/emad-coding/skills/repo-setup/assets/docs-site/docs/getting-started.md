---
last_reviewed: __TODAY__
covers:
  - justfile
# @if uv
  - pyproject.toml
  - .pre-commit-config.yaml
# @else
  - .github/actions/setup-tools/action.yml
  - .githooks/
# @endif
---

# Getting started

This page takes about five minutes. At the end you can change the repository and know that your
change passes the same checks as CI.

## What you need

| Tool | Why |
| --- | --- |
| [git](https://git-scm.com/) | The repository is a git repository. |
<!-- @if uv -->
| [uv](https://docs.astral.sh/uv/) | Installs the tools this repository uses, and the Python version in `.python-version`. You do not install Python yourself. |
<!-- @else -->
| The tools in [Contributing](contributing.md) | `just install` checks them and lists what is missing, with the install command for each. |
<!-- @endif -->
| [just](https://just.systems/) | Runs the repository's tasks. Run `just` to list them. |

## Set up

```bash
git clone https://github.com/__OWNER__/__SLUG__.git
cd __SLUG__
just install
```

<!-- @if uv -->
`just install` installs every tool in `pyproject.toml` and the git hooks. The hooks run quick
checks before each commit, and they refuse a commit message that is not a Conventional Commit.
<!-- @else -->
`just install` turns on the git hooks in `.githooks/`. They check the staged changes for
whitespace errors and secrets before each commit, and they refuse a commit message that is not a
Conventional Commit.
<!-- @endif -->

## Run the checks

```bash
just check
```

This is the same recipe that CI runs. If it passes here, CI passes.

## Make a change

1. Create a branch: `git switch -c fix/short-name`.
2. Make the change. Update the documentation in the same change.
3. Run `just check`.
4. Commit with a [Conventional Commit](https://www.conventionalcommits.org/) message, for
   example `fix: reject empty names`. The hook checks it.
5. Open a pull request. Its title must be a Conventional Commit too, because the pull request is
   squash-merged and the title becomes the commit on `__BRANCH__`.

<!-- @if release -->
After the merge, the Release workflow decides whether a new version is needed. The
[contributing guide](contributing.md) explains how.
<!-- @else -->
The [contributing guide](contributing.md) has the rest.
<!-- @endif -->

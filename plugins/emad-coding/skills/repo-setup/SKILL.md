---
name: repo-setup
description: >-
  Sets up or completes a Git repository the way Emad's PyFR project is set up, for any
  language: Conventional Commits enforced by a commit hook and a pull request title check,
  one `just check` recipe that CI runs unchanged, GitHub Actions pinned by commit SHA with
  least-privilege permissions, a MkDocs Material site on GitHub Pages with decision records
  and docs-freshness gates, link checking, Dependabot, automated releases with commitizen, a
  nightly run, optional Trivy and container image workflows, agent instruction files
  (AGENTS.md, CLAUDE.md, Copilot), and a checklist of one-time GitHub settings. Works in an
  empty folder or an existing repository and never overwrites existing files. Use whenever
  the user asks to set up, initialize, bootstrap, scaffold, standardize or harden a
  repository, to add CI, docs, releases, DevOps basics or repo hygiene to a project, or says
  "set this repo up like PyFR", even if they name only one part.
license: MIT
---

# Repo setup

This skill gives a repository the same foundation as PyFR, Emad's service template. The
foundation does not depend on the language. It rests on five rules:

1. **One definition of "the checks".** `just check` runs everything. CI runs the same recipe, so a
   failure in CI can be reproduced with one command.
2. **Releases come from commits.** Every commit message and pull request title is a Conventional
   Commit. commitizen reads them, picks the version, writes the changelog, and tags the release.
3. **Documentation ships with the change.** The docs site, decision records and docs gates keep
   prose true.
4. **Least privilege.** Every workflow starts with `permissions: {}`. Every action is pinned by
   commit SHA.
5. **Nothing happens outside the repository by surprise.** The skill writes files. It does not
   change GitHub settings, push, or create secrets. It prints a checklist instead.

## Modules

`base` is always installed. Every other module is a choice, so a request for "only X" is a
smaller set of modules, not a set of files to delete by hand.

| Module | Adds | Default |
| --- | --- | --- |
| `base` | README, licence, hooks (file hygiene, secret scan, commit-message check), `justfile`, CI job `checks`, `pr-title` check, Dependabot, PR template, contributing guide | always |
| `release` | commitizen release workflow: bump, changelog, tag, GitHub Release | on, unless the repository already has a release tool |
| `agents` | `AGENTS.md`, `CLAUDE.md`, Copilot review rules | on |
| `adr` | decision records: template, index, five starter records | on |
| `docs-site` | MkDocs Material site, getting started, glossary, roadmap, Pages deploy | on |
| `docs-gates` | docs-updated gate, docs freshness warnings, link checker (`lychee`). Needs `docs-site`. | on |
| `nightly` | scheduled run of every check | on |
| `security` | dependency review on pull requests, Trivy scan of the tree, `SECURITY.md` | on |
| `container` | multi-architecture build, Trivy image scan, SBOM, publish to GHCR. Needs `security` and `release`. | only if a `Dockerfile` exists, or the user asks |

`references/modules.md` lists every file, recipe and required check per module.

## Toolchain: how the repository's own tools run

The repository's tools (workflow lint, secret scan, commit-message check, docs build, release) must
not force a language on the project. So there are two toolchains:

| Toolchain | For | Files it adds | A contributor needs |
| --- | --- | --- | --- |
| `native` | every repository that is not Python (Go, Node, Rust, empty) | `.githooks/`, `.editorconfig`, `.github/actions/setup-tools/`, `.cz.toml` with `release` | `just` and a few small tools (`just doctor` lists them, with `brew install` lines) |
| `uv` | Python repositories, or when the user asks for it | `pyproject.toml`, `.python-version`, `.pre-commit-config.yaml`, `uv.lock` | `uv`, `just` |

`--toolchain auto` (the default) picks `uv` when the folder has a Python project file
(`pyproject.toml`, `uv.lock`, `requirements.txt`, `setup.py`) and `native` otherwise. Pass it
explicitly when you know better, for example `--toolchain uv` for a repository that already uses uv
for its tools. **Never put `uv`, a `pyproject.toml`, a `uv.lock` or a `.python-version` into a
repository that is not Python unless the user asks for it.** A Go developer should not need Python to
commit.

## Steps

`<skill dir>` is the folder that holds this SKILL.md.

### 1. Look first, change nothing

Read the repository before you ask anything. Most answers are already there.

```bash
git rev-parse --show-toplevel; git remote get-url origin
git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || git branch --show-current
ls -A; command -v just uv gh docker python3 actionlint gitleaks; git status --short
```

Note the language files (`go.mod`, `package.json`, `Cargo.toml`, `pyproject.toml`: they decide the
toolchain), any
`Makefile`, `.github/workflows/`, release tool (`release-please`, `semantic-release`, a
`.cz.toml`), `docs/` or `mkdocs.yml`, `LICENSE`, and `Dockerfile`. Run `git status --short` so you
know what the user had changed before you started.

Work out these values. **A value the user gave you wins over one you inferred.** Ask only for
what you cannot find:

| Value | Where to find it |
| --- | --- |
| `NAME` | the user's request, else the README title, else the folder name in title case |
| `SLUG` | the remote's repository name, else the folder name |
| `DESCRIPTION` | the user's request, else the first README paragraph or package metadata. One sentence. |
| `OWNER` | the remote URL, else `gh api user -q .login` |
| `AUTHOR` | the user's request, else `git config user.name` |
| `BRANCH` | the remote's default branch, else the current branch |
| `SOURCE_PREFIX` | the folders that hold the source, ending in `/` and separated by commas (`cmd/,internal/`, `src/`, `lib/`) |

`NAME`, `DESCRIPTION`, `AUTHOR` and `SOURCE_PREFIX` must not contain `"`, `\` or a line break,
because they land inside quoted YAML and TOML.

**Licence.** A licence is a legal choice, so make it only when the user asks for it.

- The repository already has a `LICENSE`: never replace it. Pass the matching `--license <id>` if
  you can tell which one it is, so the README and site footer agree, otherwise `--license none`.
- It has none, and the user asked for the full setup or named a licence: use it (default `MIT`).
- It has none, and the user asked for only some parts: `--license none`, and say so.

### 2. Ask what is left, in one message

Ask once. Put your inferred values and your default module choices in the question, so the user
can answer "yes". Skip the question when the request already answers it, or when no one can
answer (a non-interactive run). Then state your assumptions in the report.

- "Like PyFR", "everything" and "all the DevOps" mean every module that applies.
- "I only want A, B and C" means the smallest set of modules that gives A, B and C. Match each
  part to a module with the table above. For example, CI checks, the title check, Dependabot and
  a contributing guide are `base` alone, with `--license none`.
- If the repository already has a release tool, leave `release` out, and say so.
- A module the user declines is not installed. `docs-gates` needs `docs-site`, and `container`
  needs `security` and `release`.

### 3. Preview an existing repository

```bash
python3 <skill dir>/scripts/scaffold.py . --modules release,agents,adr,docs-site,docs-gates \
  --set NAME="..." --set SLUG=... --set DESCRIPTION="..." --set OWNER=... --set AUTHOR="..." \
  --set BRANCH=main --set SOURCE_PREFIX=src/ --license MIT --toolchain auto --dry-run --diff
```

It reports `created`, `same`, `differs` (the file exists with other content) and `merged`
(`.gitignore` only). Tell the user the counts and name the `differs` files. Use `--skip <glob>`
for a single file the user does not want. Read `references/existing-repos.md` now. Skip this step
for an empty folder.

### 4. Write the files

Run the same command without `--dry-run`. The script never overwrites a file. It fills in the
placeholders and drops the blocks of modules you did not choose. At the end it prints two lines you
use in the next step: the files it created, and the new workflows.

If Python is not available, copy `assets/<module>/` by hand with the same rules: strip the
`.tmpl` suffix, replace each `__NAME__`-style placeholder, keep an `@if <module>` block only
when that module is chosen, and never overwrite.

### 5. Pin, lock and verify

```bash
python3 <skill dir>/scripts/pin_actions.py <the new workflow files>   # refreshes SHA pins; needs the network
uv lock && uv sync --all-groups                                       # uv toolchain only
git add <the files that were created>                                 # so the checks see them
just install && just check
```

The `native` toolchain has no lock step. It calls programs that must be installed on the machine:
run `just doctor` first. If tools are missing, **do not install them on the user's machine yourself**
(a global `brew install` is the user's choice): list them with the install command and say that
`just check` was not run. Do not claim the repository is verified when you could not run it.

- **Pin only the new workflows**, never the whole folder. The user's own workflows may use tags,
  and they are theirs to change.
- The templates already carry SHA pins. If `pin_actions.py` fails offline, the shipped pins still
  work, so say the pins were not refreshed.
- **Stage only the files the script created**, never `git add -A`. The user may have other changes.
- **`just check` looks at every file.** With the `uv` toolchain the pre-commit hooks may also
  fix files (end-of-file, trailing whitespace). With `native`, `just hygiene` reports files that
  break `.editorconfig`, and an existing repository may have some. Compare `git status` with what
  you saw in step 1, and tell the user which of their existing files a hook changed or a check
  flagged. Do not "fix" the user's files to make the check pass without asking.
- If `just check` fails, read the error, fix it and run it again. If a tool is missing, say which
  one and give the install command. Do not claim the repository is verified when you could not run
  `just check`.
- With `container` and an existing `Dockerfile`, run `just scan-image` once if Docker is available.
  An old base image or Go version often fails the scan, and the user should hear that before the
  first release does it for them. If you cannot run it, say it is untested.

### 6. Finish the files you left alone

For each `differs` file, follow `references/existing-repos.md`: show the user what you would
add, make only additive changes, and wait for a yes before editing a file the user wrote.

In files you created, fit them to the repository without asking:

- Add the language's Dependabot ecosystem to `.github/dependabot.yml` (`gomod`, `npm`, `cargo`,
  `pip`). It is configuration only.
- Do not add the language's lint or test jobs. See "Boundaries".

### 7. Report

Keep it short. Include:

- **Created / left alone / merged**: counts, and the names of the files left alone.
- **Verification**: whether `just check` passed, and anything you could not run.
- **The toolchain** you used, and what a contributor must install (`just` and the tools that
  `just doctor` lists, or `uv` and `just`).
- **Assumptions** you made for values the user did not give, including the licence decision.
- **The checklist of one-time GitHub settings**. The new `docs/contributing.md` already holds it,
  filled in for this repository. Add the commands from `references/github-settings.md` for the
  settings that can be scripted. Do not run them. Never ask for or paste a token. The user
  creates `RELEASE_TOKEN` with `gh secret set RELEASE_TOKEN`.
- **What happens at the first merge.** With `release` installed and a `feat` or `fix` already in the
  history, the first merge to the default branch releases `v0.1.0`, and with `container` it also
  pushes an image. Say so, so the user sets the settings first.
- **Where to add the language's own checks**: the `check` recipe in the `justfile`. If you saw a
  test command, name it, for example `go test ./...` or `make test`, and offer to add it. If the
  repository has its own test workflow, say that both will run until the user removes one.
- **A suggested commit message**: `chore: set up the repository`. Do not commit or push unless
  the user asked.

## Boundaries

- **Language-agnostic on purpose.** Do not add a lint, test or build job for the language. Add
  none unless the user asks. The `check` recipe is where those go.
- **Do not overwrite.** The user's README, licence, workflows and config are theirs. Add to them
  only with a yes.
- **Do not run GitHub-changing commands.** No `gh repo edit`, no `gh api -X PUT/POST`, no
  `gh secret set`. The checklist is for the user to run.
- **Do not put Python in a repository that is not Python.** The `native` toolchain exists for that.
  Use `uv` only for a Python repository, or when the user asks.
- **Do not guess at a clash.** If an existing `pyproject.toml` cannot hold `uv` dependency groups
  (for example a Poetry 1.x project), stop and ask.
- **Write the new docs in simple, direct English.** Use short sentences, no idioms, and expand
  each acronym the first time. Do the same in anything you merge into the user's files.

## More detail

- `references/modules.md`: every file, recipe and required check, per module; how to remove a module later.
- `references/existing-repos.md`: the rules for merging into a repository that already has files.
- `references/release.md`: how commitizen releases work here, version providers for other languages, tokens, and troubleshooting.
- `references/github-settings.md`: the one-time GitHub settings, with `gh` commands for the user to run.

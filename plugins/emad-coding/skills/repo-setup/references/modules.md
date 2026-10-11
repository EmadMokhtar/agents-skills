# Modules

Every file below is written by `scripts/scaffold.py`. A module is installed when it is named in
`--modules` (`base` is always installed). Blocks in a shared file, such as the `justfile`, appear
only when their module is installed.

Contents: [base](#base) · [release](#release) · [agents](#agents) · [adr](#adr) · [docs-site](#docs-site) · [docs-gates](#docs-gates) ·
[nightly](#nightly) · [security](#security) · [container](#container) ·
[Adding the language's own checks](#adding-the-languages-own-checks) ·
[Removing a module later](#removing-a-module-later)

## base

| File | Purpose |
| --- | --- |
| `README.md`, `LICENSE` | Landing page with CI badge. Licence from `assets/licenses/`; `--license none` writes no licence and removes every mention of it. |
| Toolchain files | See [Toolchains](#toolchains). |
| `justfile` | `install`, `lint-workflows`, `precommit`, `check`. The recipes call `uv run` or the tool itself, depending on the toolchain. The native toolchain also has `doctor`. |
| `.github/workflows/ci.yml` | Job `checks`: runs `just check`. |
| `.github/workflows/pr-title.yml` | Job `pr-title`: the pull request title must be a Conventional Commit. |
| `.github/dependabot.yml` | Weekly updates for `uv`, `github-actions` and `pre-commit`, with Conventional Commit prefixes. Add the language's own ecosystem. |
| `.github/pull_request_template.md` | Checklist. |
| `docs/contributing.md` | Set up, checks, commits, one-time GitHub settings. Sections for releases, decision records and documentation appear only when those modules are installed. |
| `.gitignore` | Merged line by line into an existing file. Lines for a module appear only with that module. |

Required status checks: `checks`, `pr-title`.

## Toolchains

The repository's own tools run one of two ways. `--toolchain auto` picks `uv` when the folder has a
Python project file, and `native` otherwise.

| | `uv` | `native` |
| --- | --- | --- |
| Files | `pyproject.toml` (tooling only, `package = false`), `.python-version`, `uv.lock` (made by `uv lock`), `.pre-commit-config.yaml` | `.githooks/commit-msg`, `.githooks/pre-commit`, `.editorconfig`, `.github/actions/setup-tools/action.yml`, and with `release` a `.cz.toml` |
| Git hooks | pre-commit: file hygiene, gitleaks, commitizen message check | plain scripts: a regex check of the commit message, `git diff --check`, a gitleaks scan of the staged changes (the whole tree for the first commit) |
| Tools | Python packages pinned in `pyproject.toml` | programs each person installs: actionlint, gitleaks, editorconfig-checker, and per module commitizen, MkDocs Material, lychee, Python 3 (for two stdlib-only scripts), Trivy. CI installs the same tools at exact versions, all in `.github/actions/setup-tools/action.yml` |
| `precommit` recipe | `pre-commit run --all-files` | `hygiene` (editorconfig-checker) and `secrets` (gitleaks) |
| Dependabot | `uv`, `pre-commit` | none for the tools (it watches the actions, including the local setup action) |
| A contributor needs | `uv`, `just` | `just` and the tools `just doctor` lists, each with a `brew install` line |

The `native` toolchain is the answer to "a Go developer should not need uv". commitizen keeps its
settings in its own `.cz.toml`, so there is no `pyproject.toml`. The cost is that a laptop may run a
newer tool than CI, because exact versions are pinned only in CI. `just doctor` checks that every tool
exists; it does not check versions.
CI runs the same `just` recipes. Each job calls the local `setup-tools` action with the tools it
needs, and the action installs them with `go install` (actionlint, gitleaks, editorconfig-checker),
`pipx` (commitizen, MkDocs) or a setup action (just, Trivy).

## release

`.github/workflows/release.yml`, plus the pieces of shared files that only a release needs: the
`next-version` and `changelog` recipes, the commitizen bump settings in `pyproject.toml`, the
Releases section and the `RELEASE_TOKEN` setting in `docs/contributing.md`. Leave this module out
when the repository already has a release tool: the commit hook and the title check still work with
any of them. See `release.md`.

## agents

`AGENTS.md`, `CLAUDE.md` (only contains `@AGENTS.md`) and `.github/copilot-instructions.md`.

## adr

`docs/adr/`: `template.md`, `README.md` and five records (record decisions, Conventional Commits,
one check recipe, pin actions and limit permissions, run the tools the same way everywhere). The ADR links in the site navigation, the
glossary and the contributing guide appear only with this module.

## docs-site

`mkdocs.yml`, `docs/index.md`, `docs/getting-started.md`, `docs/glossary.md`, `docs/roadmap.md`,
`.github/workflows/docs.yml` (build, then deploy to GitHub Pages). Adds `docs` and `docs-build` to
the `justfile`, a `docs` dependency group, and `docs-build` to `check`.

Pages carry `last_reviewed: <date>` in their front matter. Every new page must be added to `nav`,
or `mkdocs build --strict` fails. `docs/adr/template.md` is excluded from the site.

## docs-gates

Needs `docs-site`.

- `scripts/check_docs_updated.py`: fails a pull request that changes `SOURCE_PREFIX` but no
  documentation. The `no-docs-needed` label skips it. Stdlib only.
- `scripts/check_docs_freshness.py`: warns about pages not reviewed for 180 days, and pages whose
  `covers:` files changed while the page did not. It never fails. Needs only Python 3 and its standard library.
- `lychee.toml` and the `links` job: external link check. It is not a required check, because it
  depends on the network.
- `.github/workflows/docs-gates.yml`: jobs `docs-updated`, `docs-warnings`, `links`.

Required status check added: `docs-updated`. The label `no-docs-needed` must exist.

## nightly

`.github/workflows/nightly.yml` runs `just check` every night at 03:17 UTC. It adds a full link
sweep when `docs-gates` is installed, `just scan-tree` when `security` is installed, and a scan of
the last published image when `container` is installed. A check can start failing with no commit,
because a link dies or an advisory is published, and this is how someone notices.

## security

- `.github/workflows/security.yml`: jobs `dependency-review` (pull requests only) and `scan-tree`.
- `ops/trivy/.trivyignore.yaml`: the only way to exempt a finding. Every entry must say why and
  must expire.
- `SECURITY.md`: how to report a vulnerability privately.
- `justfile`: `scan-tree`, which calls the `trivy` program (`brew install trivy`). CI installs Trivy
  at an exact version with `aquasecurity/setup-trivy`.

Required status checks added: `dependency-review`, `scan-tree`. `dependency-review` needs the
dependency graph; on a private repository it also needs GitHub Advanced Security. If that is not
available, tell the user to delete the job rather than leave a check that always fails.

## container

Needs `security` and `release`, and a `Dockerfile` at the repository root. The skill does not write a
Dockerfile, because that depends on the language. If the Dockerfile lives elsewhere, edit the
`build-image` and `build-multiarch` recipes.

- `.github/workflows/container.yml`: jobs `build` (amd64 and arm64, no push) and `scan` (Trivy and
  an SBOM artifact).
- `.github/workflows/publish-images.yml`: reusable. Called by `release.yml` after a release. Pushes
  to `ghcr.io/<owner>/<repo>`, scans both platforms, attaches the SBOM to the GitHub Release, then
  moves `latest`.
- `justfile`: `build-image`, `build-multiarch`, `scan-image`, `sbom`. Dependabot also watches the
  Dockerfile's base images.

The publish workflow could only be checked with actionlint, not run against a real registry. Say
so in the report.

## Adding the language's own checks

The skill adds no language checks. The user adds them to the `check` recipe, and CI runs them
automatically because CI runs `just check`. Offer the matching lines when you see the language:

| Seen | Recipes to add | Dependabot ecosystem |
| --- | --- | --- |
| `go.mod` | `test: go test ./...` and `lint: golangci-lint run`, then `check: ... test lint` | `gomod` |
| `package.json` | `test: npm test` and `lint: npm run lint` | `npm` |
| `Cargo.toml` | `test: cargo test` and `lint: cargo clippy -- -D warnings` | `cargo` |
| Python with pytest and ruff | `test: uv run pytest` and `lint: uv run ruff check . && uv run ruff format --check .` | `uv` (already present) |
| A `Makefile` with a `test` target | `test: make test` | none |

Add the Dependabot ecosystem to `.github/dependabot.yml` yourself. It is configuration only, and the
file is one you created.

The language's own toolchain must also be installed in CI. Add its setup action to `ci.yml`
(pinned by SHA, with `pin_actions.py`) before the `just check` step.

## Removing a module later

Delete the module's files, then remove the module's lines from the shared files: the `justfile`
recipes, the `check` dependency, the `docs` group in `pyproject.toml`, and the matching required
status checks in the ruleset. Run `uv lock` and `just check`.

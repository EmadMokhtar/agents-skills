# Existing repositories

Use this when `scaffold.py` reports `differs`, or when the repository already has tooling the
skill would add. The user's files come first. Every rule below follows from that.

## Before you change anything

List what is already there, and say it to the user in one short list: language files, test or
build commands, workflows, release tool, docs, pre-commit config, `Dockerfile`, agent files. A
repository that already has a thing the skill adds does not need it twice.

## Per file

| File that exists | What to do |
| --- | --- |
| `README.md` | Keep it. Offer to add the CI badge, the documentation link and a Contributing section. |
| `LICENSE` | Never replace it, even a one-line stand-in. Pass the matching `--license <id>`, or `--license none`, so the README and site footer agree with it. You may offer to replace a stand-in with the full text. |
| `.gitignore` | Merged automatically: missing lines are appended under a heading. |
| `justfile` | Show the template's recipes. Add the ones whose names are free. Make `check` depend on the new gates. Keep the user's recipes unchanged. |
| `Makefile` only | Keep it. `just` is added next to it, because CI runs `just check`. Offer `test: make test` in the `justfile` and add `test` to `check`, so the two do not drift. |
| `pyproject.toml` | A Python repository, so the toolchain is `uv`. Add `[dependency-groups]` (`dev`, and `docs` when `docs-site` is installed) and `[tool.commitizen]`. Leave `[project]` and every other table alone. Then `uv lock`. If the file has no `[project]` table (Poetry 1.x), stop and ask. |
| `package.json`, `go.mod`, `Cargo.toml` | Keep them. These repositories get the `native` toolchain, so nothing Python is added. The commitizen settings go in `.cz.toml`; pick the version provider in `release.md`. |
| `.editorconfig` | Keep it. The `native` toolchain's `just hygiene` checks files against it, so existing files may be flagged. Say so, and do not rewrite the user's files. |
| `.githooks/` or another `core.hooksPath` | Do not change the user's hook setup. Tell them `just install` would point git at `.githooks`, and ask. |
| `.pre-commit-config.yaml` | The user already uses pre-commit, so choose `--toolchain uv` only if the repository is Python. Otherwise keep their file and add the missing hooks: `gitleaks`, and the local `commitizen` commit-message hook. Keep the user's hooks and their pinned versions. Make sure `default_install_hook_types` includes `commit-msg`. |
| `.github/workflows/*.yml` | Keep every file. Never run `pin_actions.py` on them: only on the workflows you created. If a workflow already runs the tests, say that `ci.yml` is new and that both will run. Offer to move the test command into `just check` and delete the old job. Do not do it without a yes. |
| `release-please`, `semantic-release`, or another release tool | Do not add a second one. Leave the `release` module out and tell the user. Keep `pr-title.yml` and the commit hook: they work with any of them. A release pull request opened with `GITHUB_TOKEN` does not start other workflows, so a required `checks` or `pr-title` blocks it. The fix is a personal access token passed to the release tool. Mention this when the user will require those checks. |
| `docs/` or `mkdocs.yml` | Do not install `docs-site` over it. Ask. If the user has a site, install `base` only, and offer to add the decision records to their `nav`. |
| `AGENTS.md` / `CLAUDE.md` | Keep them. Offer to append the "Commits and pull requests" and "GitHub Actions" sections from the template. If only `CLAUDE.md` exists, leave it as it is. |
| `.github/dependabot.yml` | Add the missing `package-ecosystem` entries only. Keep the user's schedules and groups. |
| `.github/pull_request_template.md` | Keep it. Offer the Conventional Commits line. |

## Hooks can change the user's files

`just check` runs the pre-commit hooks over every file. Fixer hooks (end-of-file, trailing
whitespace) may edit files the user wrote. Compare `git status` before and after, and tell the user
which existing files changed.

## Making an edit

1. Run `scaffold.py --dry-run --diff` and read the diff for that file.
2. Tell the user what you would add, in one or two lines.
3. After a yes, make the smallest additive edit. Do not reformat the rest of the file.
4. Run `just check` again.

If the user says no, leave the file as it is and list it under "left alone" in the report.

## Things that look like clashes but are not

- A repository with its own `.venv`, `.python-version` or lock file: the skill adds a tooling
  `pyproject.toml` only when none exists. With a different Python version pinned, keep the user's
  version, and make sure it is 3.13 or newer for the tooling, or lower `requires-python` in the
  tooling file.
- A monorepo, or source in several folders: install at the root and list every source folder in
  `SOURCE_PREFIX`, separated by commas (`--set SOURCE_PREFIX=cmd/,internal/`).
- A repository with a default branch other than `main`: pass `--set BRANCH=<name>`.

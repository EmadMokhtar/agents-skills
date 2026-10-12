# Releases

This is the `release` module. commitizen (a tool that reads Conventional Commits) makes every
release. The generated `release.yml` runs on each push to the default branch. With the `native`
toolchain commitizen is a program on the machine (`brew install commitizen`) that reads its settings
from `.cz.toml`, so the repository needs no `pyproject.toml`. With `uv` it runs through `uv run`. If the repository already has another release tool, do not
install this module.

## What happens on a push

1. `cz bump --yes --changelog` reads the commits since the last tag.
2. If a commit is releasable (`feat`, `fix`, or a breaking change), it picks the next version,
   writes `CHANGELOG.md`, commits `bump: version X → Y`, and creates the tag `vY`.
3. The workflow pushes the commit and the tag together (`git push --atomic`).
4. It publishes a GitHub Release with that version's changelog section as the notes.
5. With the `container` module, it calls `publish-images.yml` for the new version.

If nothing is releasable, `cz bump` exits with code 3 (no new commits) or 21 (new commits, but
only `docs`, `chore` and similar types). The workflow treats both as "nothing to do".

The bump commit starts with `bump:`. The workflow skips pushes whose message starts with
`bump:`, or it would start itself forever.

## Version rules

| Commit | Before 1.0.0 | From 1.0.0 |
| --- | --- | --- |
| `fix:`, `perf:` | patch | patch |
| `feat:` | minor | minor |
| `feat!:` or a `BREAKING CHANGE:` footer | minor (`major_version_zero = true`) | major |
| `docs`, `chore`, `ci`, `build`, `test`, `style`, `refactor` | no release | no release |

The first release of a new repository is `v0.1.0`, made by the first `feat` or `fix`. To move to
`1.0.0` on purpose, remove `major_version_zero` and make a breaking change, or tag by hand.

## The version provider

The generated commitizen settings (in `pyproject.toml` with the `uv` toolchain, in `.cz.toml` with
`native`) use `version_provider = "scm"`. The version is the newest git tag,
so no file stores it, and the setup works for every language. Keep it unless the repository
already stores its version in a file that other tools read:

| The repository has | Set `version_provider` to | commitizen also updates |
| --- | --- | --- |
| nothing, or Go (`go.mod`) | `scm` | nothing |
| `package.json` | `npm` | `package.json`, `package-lock.json` |
| `Cargo.toml` | `cargo` | `Cargo.toml`, `Cargo.lock` |
| `composer.json` | `composer` | `composer.json` |
| `pyproject.toml` with `[project] version` | `pep621` | `pyproject.toml` |
| the same, managed with uv | `uv` | `pyproject.toml` and `uv.lock` |
| Poetry | `poetry` | `pyproject.toml` |

Use `version_files = ["path/to/file:PATTERN"]` to update any other file that holds the version
(for example `plugin.json`), then pass `--check-consistency` (the workflow already does) so a bump
that cannot find the old value fails instead of leaving the file behind.

## Tokens and branch protection

The bump commit is a push to the protected default branch. The default `GITHUB_TOKEN` cannot do
that when a ruleset requires pull requests. So:

- Create a fine-grained personal access token for this repository only, with *Contents* set to
  read and write, from an account that may bypass the ruleset.
- Store it with `gh secret set RELEASE_TOKEN`. The user does this. Do not ask for the value.
- The workflow uses `RELEASE_TOKEN` when it exists and falls back to `GITHUB_TOKEN`. A push made
  with a personal token also starts the other workflows. A push made with `GITHUB_TOKEN` does not.

## Previewing

`just next-version` shows the version the next release would have. `just changelog` shows the
changelog entry. Both change nothing.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `The push was refused` in the Release job | The branch is protected. Add `RELEASE_TOKEN`, and let its owner bypass the ruleset. |
| The Release job failed after the tag was pushed, so there is a tag but no GitHub Release | Run the Release workflow by hand (Actions, Release, Run workflow). It finds the newest tag, sees that it has no GitHub Release, and creates it. With `container`, it also publishes the images. Pushes are skipped on purpose after a `bump:` commit, so waiting does not help. |
| The images were not published, but the GitHub Release exists | Run the Publish images workflow by hand, with the version. |
| No release after a merge | Every commit since the last tag is `docs`, `chore`, `ci` or similar. A change to behaviour should have been `feat` or `fix`. Fix the habit; rewriting history is not needed. |
| A release was skipped for a `feat` | The pull request title was not a Conventional Commit, so the squash commit hid it. The `pr-title` check exists to prevent this. |
| `[NO_COMMITS_TO_BUMP]` locally | Exit code 21. Not an error. |
| Release workflow runs twice | Check that the bump commit message still starts with `bump:`. |
| `uv lock --check` fails after a bump | The `scm` provider does not touch the lock file. With the `uv` provider, use `uv` and not `pep621`, so the lock file changes with the version. |

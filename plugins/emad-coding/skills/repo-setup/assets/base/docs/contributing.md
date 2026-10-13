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
  - .github/workflows/ci.yml
# @if release
  - .github/workflows/release.yml
# @endif
---

# Contributing

## Set up

<!-- @if uv -->
You need [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

- **uv** installs the tools this repository uses. It also fetches the Python version named in
  `.python-version`, so you do not install Python yourself.
- **just** runs the repository's tasks. Run `just` to list them.

```bash
just install
```

This installs every tool and the git hooks. The hooks run the quick checks before each commit,
and they reject a commit message that is not a Conventional Commit.
<!-- @else -->
You install these tools yourself. The commands below use [Homebrew](https://brew.sh/); use your
own package manager if you prefer. CI installs the same tools at pinned versions (see
`.github/actions/setup-tools/action.yml`). This repository keeps no Python project or lock file
for its tools.

| Tool | What it does | Install |
| --- | --- | --- |
| [just](https://just.systems/) | Runs the repository's tasks. | `brew install just` |
| [actionlint](https://github.com/rhysd/actionlint) | Lints the GitHub Actions workflows. | `brew install actionlint` |
| [gitleaks](https://github.com/gitleaks/gitleaks) | Scans for secrets. | `brew install gitleaks` |
| [editorconfig-checker](https://github.com/editorconfig-checker/editorconfig-checker) | Checks file endings and whitespace. | `brew install editorconfig-checker` |
<!-- @if release -->
| [commitizen](https://commitizen-tools.github.io/commitizen/) | Reads Conventional Commits to make releases. | `brew install commitizen` |
<!-- @endif -->
<!-- @if docs-site -->
| [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) | Builds the documentation site. | `brew install mkdocs-material` |
<!-- @endif -->
<!-- @if docs-gates -->
| [lychee](https://lychee.cli.rs/) | Checks the external links. | `brew install lychee` |
| Python 3 | Runs the two small scripts in `scripts/`. It needs no packages. | `brew install python` |
<!-- @endif -->
<!-- @if security -->
| [Trivy](https://trivy.dev/) | Scans for known vulnerabilities, secrets and bad configuration. | `brew install trivy` |
<!-- @endif -->

```bash
just install
```

This turns on the git hooks in `.githooks/`, then runs `just doctor`, which lists any tool you are
missing. Before each commit the hooks check the staged changes for whitespace errors and secrets,
and they reject a commit message that is not a Conventional Commit.
<!-- @endif -->

## The checks

`just check` runs every check that works on your machine alone, and the `checks` job in CI runs
the same recipe. If it passes on your machine, that job passes too.
<!-- @if ciextras -->

CI also runs gates that need GitHub or the network. They are not part of `just check`, so run
them by hand when you change what they cover:

<!-- @if docs-gates -->
- `docs-updated` and `docs-warnings` compare a pull request with its base branch, so they run
  on pull requests. By hand: `just docs-updated` and `just docs-freshness`. The `links` job needs
  the network: `just links`.
<!-- @endif -->
<!-- @if security -->
- `dependency-review` runs on GitHub only. `scan-tree` needs Trivy and the network: `just scan-tree`.
<!-- @endif -->
<!-- @if container -->
- `build` and `scan` build the image: `just build-multiarch` and `just scan-image`.
<!-- @endif -->
<!-- @endif -->

| Recipe | What it checks |
| --- | --- |
| `just lint-workflows` | The GitHub Actions workflows, with actionlint |
<!-- @if uv -->
| `just precommit` | Every pre-commit hook over every tracked file: file hygiene, secret scanning |
<!-- @else -->
| `just precommit` | `just hygiene` (file endings and whitespace, as `.editorconfig` says) and `just secrets` (secret scan) |
<!-- @endif -->
<!-- @if docs-site -->
| `just docs-build` | The documentation site builds with `--strict` |
<!-- @endif -->
<!-- @if docs-gates -->
| `just docs-freshness` | Warns about stale pages. It never fails. |
<!-- @if uv -->
| `just links` | The external links still work. It needs the `lychee` program, so CI runs it separately. |
<!-- @else -->
| `just links` | The external links still work. It needs the network, so CI runs it separately. |
<!-- @endif -->
<!-- @endif -->
<!-- @if security -->
| `just scan-tree` | Known vulnerabilities, secrets and bad configuration, with Trivy. It needs the `trivy` program. |
<!-- @endif -->
<!-- @if container -->
| `just scan-image` | The built image, with Trivy. It needs Docker and the `trivy` program. |
<!-- @endif -->

Add your language's own checks to the `check` recipe in the `justfile`, for example `test`,
`lint` and `typecheck`. CI runs whatever `check` runs.

## Commits and pull request titles

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for every commit
and every pull request title:

```text
<type>[scope][!]: <description>
```

Types are `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`, `style`
and `revert`. The description is lowercase, in the imperative mood, with no final period. Mark
a breaking change with `!` after the type, and explain it in a `BREAKING CHANGE:` footer.

Pull requests are squash-merged, so the title becomes the commit on `__BRANCH__`.
<!-- @if release -->
The release workflow reads that commit. A title such as `Update auth` would hide a fix from the
release.

A change to what the software does is `feat` or `fix`, even if the files are Markdown. `docs`,
`chore`, `ci`, `build`, `test`, `style` and `refactor` do not cause a release.
<!-- @else -->
The tool that makes releases reads that commit, so a title such as `Update auth` would hide a fix
from the release.

A change to what the software does is `feat` or `fix`, even if the files are Markdown.
<!-- @endif -->
<!-- @if release -->

## Releases

[commitizen](https://commitizen-tools.github.io/commitizen/) (a tool that reads Conventional
Commits) makes every release. You do not edit a version number or `CHANGELOG.md`.

1. Merge a pull request with a `feat`, `fix` or breaking change.
2. The Release workflow picks the next version: `feat` raises the minor number, `fix` the
   patch number, and a breaking change raises the minor number before 1.0.0 and the major
   number after it.
3. It writes `CHANGELOG.md`, commits it as `bump: version X → Y`, tags `vY`, and publishes a
   GitHub Release with the notes.

The version is the newest git tag, so no file stores it. To preview the next release, run
`just next-version` and `just changelog`. Both change nothing.
<!-- @else -->

## Releases

Releases are made by the tool this repository already uses. It reads the same Conventional
Commits, so the commit messages and pull request titles still matter.
<!-- @endif -->

<!-- @if docs-site -->
## Documentation

Write for a reader who knows nothing about this repository. Use simple, direct English: short
sentences, no idioms, and each acronym expanded the first time.

- Pages live in `docs/`. Add a new page to `nav` in `mkdocs.yml`, or the build fails.
- Every page starts with `last_reviewed: <date>` in its front matter. Update the date when you
  re-read the page and it is still true.
<!-- @if adr -->
- A decision record in `docs/adr/` must be listed in `nav` as well.
<!-- @endif -->
- A page may list the files it describes under `covers:`. When one of them changes and the page
  does not, `just docs-freshness` warns.
- Preview the site with `just docs`.
<!-- @if docs-gates -->
- A pull request that changes __SOURCE_TEXT__ must also change documentation. If the change
  needs no documentation, add the `no-docs-needed` label to the pull request.
<!-- @endif -->

<!-- @endif -->
<!-- @if adr -->
## Decision records

A decision that is hard to undo, or that a newcomer would question, gets a short record in
`docs/adr/`. ADR means Architecture Decision Record. Copy `docs/adr/template.md`, take the next
number, and list it in `docs/adr/README.md`. An accepted record is history, so never edit it. To
change a decision, write a new record and mark the old one *Superseded*.

<!-- @endif -->
## One-time repository settings

These cannot be set from a file. Set them once in the GitHub settings of
`__OWNER__/__SLUG__`.

- **Pull requests:** allow squash merging only, with the pull request title as the commit
  title. Turn on automatic deletion of merged branches.
- **Ruleset for `__BRANCH__`:** require a pull request, block force pushes, and require these
  status checks:
  - `checks` and `pr-title`
<!-- @if docs-gates -->
  - `docs-updated`
<!-- @endif -->
<!-- @if security -->
  - `dependency-review` and `scan-tree`
<!-- @endif -->
<!-- @if container -->
  - `build` and `scan`
<!-- @endif -->
<!-- @if release -->
- **Secret `RELEASE_TOKEN`:** a fine-grained personal access token for this repository only,
  with *Contents* set to read and write. The Release workflow pushes the bump commit to
  `__BRANCH__`, and a protected branch refuses the default `GITHUB_TOKEN`. Let the token's owner
  bypass the ruleset. A push made with this token also starts the other workflows.
<!-- @endif -->
<!-- @if docs-site -->
- **Pages:** set the source to *GitHub Actions*. The first docs deploy fails until you do.
<!-- @endif -->
<!-- @if docs-gates -->
- **Label `no-docs-needed`:** create it. The docs gate reads it.
<!-- @endif -->
<!-- @if security -->
- **Security:** turn on the dependency graph, Dependabot alerts and Dependabot security
  updates, and private vulnerability reporting. The dependency review check needs the graph.
<!-- @endif -->
<!-- @if container -->
- **Packages:** after the first release, open the new package in GitHub Packages and link it
  to this repository. Make it public if the image should be.
<!-- @endif -->

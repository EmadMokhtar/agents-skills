# repo-setup

Sets up a new Git repository, or completes an existing one, the way
[PyFR](https://github.com/EmadMokhtar/pyfr) is set up: documentation, checks, releases and
security from the first day. It works for any language.

## When it triggers

- You ask the agent to set up, initialize, bootstrap or scaffold a repository.
- You ask to add CI, a documentation site, automated releases or Dependabot to a project.
- You say "set this repo up like PyFR", or "add the DevOps basics".

## What you get

`base` is always installed. The other modules are choices that you confirm once.

| Module | What it adds |
| --- | --- |
| `base` | README, licence, pre-commit hooks (file hygiene, secret scan, commit-message check), a `justfile`, CI, a pull request title check, Dependabot, and a contributing guide |
| `release` | Releases with commitizen: version, changelog, tag and GitHub Release. Left out when the repository already has a release tool. |
| `agents` | `AGENTS.md`, `CLAUDE.md` and Copilot review rules |
| `adr` | Decision records: a template, an index and five starter records |
| `docs-site` | A MkDocs Material site deployed to GitHub Pages |
| `docs-gates` | A check that fails a pull request that changes source code but no documentation, warnings for stale pages, and a link checker |
| `nightly` | A scheduled run of every check, so a check that starts failing is noticed |
| `security` | Dependency review on pull requests, a Trivy scan of the tree, and `SECURITY.md` |
| `container` | Multi-architecture image build, Trivy image scan, SBOM, and publishing to GHCR on release. Only when a `Dockerfile` exists. |

A request for "only the CI checks and Dependabot" is a smaller set of modules, not a list of files
to delete. The licence is a separate choice: with `--license none` the skill writes none.

## The ideas behind it

- **One definition of "the checks".** `just check` runs everything, and CI runs the same recipe.
- **Releases come from commits.** Every commit and pull request title is a
  [Conventional Commit](https://www.conventionalcommits.org/). commitizen picks the version,
  writes the changelog, and tags the release. The version is the git tag, so it works for every
  language.
- **Least privilege.** Every workflow starts with `permissions: {}`, and every action is pinned
  by commit SHA.
- **Nothing outside the repository changes by surprise.** The skill writes files. It does not
  change GitHub settings, push, or create secrets. It gives you the checklist and the `gh`
  commands, and you run them.

## In an existing repository

The skill reads what is there first. It never overwrites a file. A file that already exists is
left alone and listed, and you decide whether the skill adds to it. The `.gitignore` is the one
file that is merged automatically, line by line. If the repository already has a release tool,
the skill leaves the `release` module out.

## Toolchain: no Python in a Go repository

The repository's own tools (workflow lint, secret scan, commit-message check, docs build, release)
run one of two ways. In a repository that is not Python, they are programs that each person installs
(`just install` runs `just doctor`, which lists what is missing and the `brew install` line for it).
CI installs the same tools at exact versions, all in one file, and the git hooks are plain scripts.
commitizen keeps its settings in its own `.cz.toml`. The repository gets no
`pyproject.toml`, no `uv.lock` and no `.python-version`. In a Python repository, or when you ask for
it, they run through `uv` instead. The skill picks by looking for a Python project file.

## Language checks

The skill adds no lint or test job for your language. Add them to the `check` recipe in the
`justfile`, and CI runs them automatically. The skill names the command it saw, such as
`go test ./...`, and offers to add it.

## What is in this folder

| Path | What it is |
| --- | --- |
| `SKILL.md` | The instructions the agent reads |
| `scripts/scaffold.py` | Copies the templates without overwriting, and fills in the placeholders |
| `scripts/pin_actions.py` | Pins GitHub Actions to the newest commit SHA of their major version |
| `assets/` | The templates, one folder per module |
| `references/` | Details the agent loads when it needs them |
| `evals/` | Test cases |

## Keeping the templates current

The templates carry SHA pins. To refresh them, run this from the repository root, and then run
`just check`:

```bash
python3 plugins/emad-coding/skills/repo-setup/scripts/pin_actions.py plugins/emad-coding/skills/repo-setup/assets
```

The tests in `tests/test_repo_setup_skill.py` render every module combination and check the
result with actionlint, a YAML and TOML parse, and the same pin and permission rules this
repository uses for its own workflows.

## What was not tested end to end

The `container` module's publish workflow ran only through actionlint, not against a real
registry. The Docker recipes (`build-image`, `build-multiarch`, `scan-image`, `sbom`) were run
locally.

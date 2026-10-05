# Plugin repository design

**Date:** 2026-10-05
**Status:** draft — awaiting review
**Repository:** `EmadMokhtar/agents-skills`
**Scope:** set up the repository that holds every agent skill Emad builds, packaged as
plugins, with a landing page, a documentation site, quality checks, releases, and one
example skill. The "initialise a repository the way I like" skill is the **next** spec, not
this one.

## 1. Why

Emad builds agent skills across different areas (job search, coding, and more). Today they
are scattered: some live inside other projects (for example `writing-skill-evals` in
`skill-evaluator`), and some exist only in a claude.ai account. There is no single place to
install them from, no published documentation, and no check that a skill is well-formed or
still behaves as intended.

This repository becomes that single place. It must:

1. hold every skill, grouped by category;
2. be installable from Claude Code **and** from other agent tools that read `SKILL.md`;
3. follow the [Agent Plugins v1.0.0](https://agent-plugins.org/specification) standard;
4. have a landing page and a documentation site in the same style as `skill-evaluator` and
   `pyfr`;
5. check every skill in CI (continuous integration), and run real evaluations on demand.

## 2. Shared understanding

### 2.1 What Emad stated

- One repository for all skills, grouped by category directories such as `jobs/<skill>` and
  `coding/<skill>`.
- It ships as a plugin.
- Follow the Agent Plugins standard (<https://agent-plugins.org/>).
- A landing page and a docs page like `skill-evaluator` and `pyfr`.
- Audience: mainly Emad, on every machine, but public so other people can install the skills.
- Tools: Claude Code, plus other tools that read the open Agent Skills format (Codex, GitHub
  Copilot, Cursor, …).
- Plugin names carry a prefix (`emad-jobs`, not `jobs`).
- The first pull request carries the repository structure plus one small real skill.
- Quality: structure checks plus `skill-lens` evaluations.
- Real evaluations run locally, and in CI only when asked for.
- Releases: release-please, one version per plugin.
- Example skill: `conventional-commits`.
- Skill documentation pages are generated from the skill files.

### 2.2 What this spec assumes

- The older `EmadMokhtar/skills` repository (documentation only, no skills) is replaced by
  this one, not merged into it.
- Process files follow Emad's other repositories: `docs/superpowers/specs|plans` (kept in
  the repository, excluded from the site), Conventional Commits for commits **and** pull
  request titles, a pull request template, Copilot review instructions, Python 3.13 with
  `uv` and `just`.
- MkDocs Material stays the site generator, to match the other two repositories, although its
  maintainers now develop its successor, Zensical. Moving all three repositories is a
  separate piece of work.

### 2.3 Success criteria

The work is done when all of the following are true:

1. `/plugin marketplace add EmadMokhtar/agents-skills` then
   `/plugin install emad-coding@emad-skills` works in Claude Code, and
   `/emad-coding:conventional-commits` is available.
2. `copilot plugin install EmadMokhtar/agents-skills:plugins/emad-coding` works in GitHub
   Copilot CLI.
3. `npx skills add EmadMokhtar/agents-skills --list` lists `conventional-commits`.
4. The site at `https://emadmokhtar.github.io/agents-skills/` is published and shows the
   catalog and a page for `conventional-commits`.
5. `just check` passes locally and CI is green on the pull request.
6. `just eval emad-coding/conventional-commits` passes through a local Claude Code.

## 3. The constraint that shapes the layout

Agent Plugins v1.0.0 §7.1: a client discovers skills only at
`skills/<name>/SKILL.md` — "Clients MUST NOT recursively search deeper descendants". §5.2:
the manifest is `plugin.json` at the plugin root, with a **closed** schema (only `$schema`,
`name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`,
`extensions` are allowed), so there is no field to point at extra skill directories.

A layout like `skills/jobs/<skill>/SKILL.md` inside one plugin is therefore invisible to every
conformant client. **Decision: one plugin per category.** The category directory still groups
the skills — `plugins/emad-jobs/skills/<skill>/` — and the layout is fully standard. A user
installs only the categories they want. (ADR 0001 records this.)

## 4. Client support

Researched on 2026-10-05 from each client's documentation and, where the documentation was
silent, its source code. Claude Code was tested in an isolated configuration directory.

| Client | Install | Catalog file it reads | Manifest it reads |
| --- | --- | --- | --- |
| Claude Code | `/plugin marketplace add EmadMokhtar/agents-skills`, then `/plugin install emad-coding@emad-skills` | `.claude-plugin/marketplace.json` | `.claude-plugin/plugin.json` (optional; absent here, so the catalog entry is the manifest). Observed, not documented: it reads `version` from the root `plugin.json`. |
| GitHub Copilot CLI | `copilot plugin install EmadMokhtar/agents-skills:plugins/emad-coding`, or via the catalog | `marketplace.json` at the root, `.plugin/`, `.github/plugin/`, or `.claude-plugin/` | root `plugin.json` (Agent Plugins) |
| VS Code | setting `chat.plugins.marketplaces`, or "Chat: Install Plugin From Source" | same order as Copilot (source code only) | root `plugin.json` (Agent Plugins) |
| OpenAI Codex | `codex plugin marketplace add EmadMokhtar/agents-skills`, then `/plugins` | documented: `.agents/plugins/marketplace.json`; source code also tries `.claude-plugin/marketplace.json` | root `plugin.json` (Agent Plugins) |
| Cursor | no documented GitHub install for normal users | `.cursor-plugin/marketplace.json` (Cursor Marketplace or Team plans only) | root `plugin.json` or `.cursor-plugin/plugin.json` |
| `npx skills` (Vercel) | `npx skills add EmadMokhtar/agents-skills --skill <name>`, `-a <tool>` picks the target tool | uses `.claude-plugin/marketplace.json` to find each plugin's `skills/` | does not read `plugin.json` |

Consequences:

- Claude Code validation (`claude plugin validate --strict`) **fails** if a plugin also carries
  a `.claude-plugin/plugin.json` copy that contains `extensions`. So plugins carry **only** the
  standard root `plugin.json`.
- Two catalog files cover every client except Cursor. Cursor users install skills through
  `npx skills add … -a cursor`. A Cursor catalog is out of scope until someone needs it.
- `npx skills` installs every skill into one flat directory and silently drops a duplicate
  name. **Skill names must be unique across the whole repository**, not only within a plugin.

## 5. Repository layout

```
.claude-plugin/marketplace.json        generated — Claude Code, Copilot, VS Code, npx skills
.agents/plugins/marketplace.json       generated — Codex (its documented path)
plugins/
  emad-coding/
    plugin.json                        Agent Plugins 1.0.0 manifest — the source of truth
    CHANGELOG.md                       written by release-please
    skills/
      conventional-commits/
        SKILL.md                       what the agent reads
        README.md                      human documentation, shown on the site
        evals/conventional-commits.eval.yaml
schemas/agent-plugins/1.0.0/plugin.schema.json   stored copy, so CI never downloads it
scripts/
  sync_catalogs.py                     plugin.json files → both catalog files
  gen_skill_pages.py                   SKILL.md + README.md → site pages (run by MkDocs)
  new_plugin.py                        scaffold a plugin and register it everywhere
  new_skill.py                         scaffold a skill inside a plugin
tests/                                 pytest — layout rules and script unit tests
docs/                                  MkDocs source (see §8)
.github/                               workflows, PR template, Copilot instructions, Dependabot
mkdocs.yml  pyproject.toml  uv.lock  justfile  .pre-commit-config.yaml  .python-version
release-please-config.json  .release-please-manifest.json
README.md  AGENTS.md  CLAUDE.md  LICENSE
```

Only categories that contain at least one skill exist. `emad-jobs` arrives together with its
first skill. There are no empty plugins.

## 6. Manifests and catalogs

### 6.1 `plugins/<plugin>/plugin.json`

The single source of truth for a plugin. Example:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "emad-coding",
  "version": "0.1.0",
  "description": "Coding workflow skills: commit messages, pull request titles, and more.",
  "author": { "name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar" },
  "homepage": "https://emadmokhtar.github.io/agents-skills/skills/emad-coding/",
  "repository": "https://github.com/EmadMokhtar/agents-skills",
  "license": "MIT",
  "keywords": ["coding", "git", "conventional-commits"]
}
```

Rules:

- `name` matches the directory name and the pattern `^emad-[a-z0-9]+(-[a-z0-9]+)*$`. This is
  stricter than Agent Plugins (no periods), so the name is also valid for Claude Code and
  avoids its reserved prefixes (`claude-`, `anthropic-`).
- `version` is present, and only here. Catalogs never carry a version, so they cannot
  disagree with it.
- No `extensions` key until a real client-specific need appears.
- No author email: the repository is public.

### 6.2 `.claude-plugin/marketplace.json` (generated)

```json
{
  "name": "emad-skills",
  "description": "Emad Mokhtar's agent skills, one plugin per category.",
  "owner": { "name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar" },
  "plugins": [
    {
      "name": "emad-coding",
      "source": "./plugins/emad-coding",
      "description": "Coding workflow skills: commit messages, pull request titles, and more.",
      "author": { "name": "Emad Mokhtar", "url": "https://github.com/EmadMokhtar" },
      "homepage": "https://emadmokhtar.github.io/agents-skills/skills/emad-coding/",
      "repository": "https://github.com/EmadMokhtar/agents-skills",
      "license": "MIT",
      "keywords": ["coding", "git", "conventional-commits"]
    }
  ]
}
```

`source` always starts with `./`: Claude Code and Codex require it, and Copilot accepts it.

### 6.3 `.agents/plugins/marketplace.json` (generated)

```json
{
  "name": "emad-skills",
  "interface": { "displayName": "Emad's skills" },
  "plugins": [
    {
      "name": "emad-coding",
      "source": { "source": "local", "path": "./plugins/emad-coding" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Coding"
    }
  ]
}
```

The allowed values of `category`, and whether `interface` is required, are checked against
the Codex documentation during planning (see §13).

### 6.4 `scripts/sync_catalogs.py`

Reads every `plugins/*/plugin.json` in name order and writes both catalog files, with stable
formatting (two-space indent, trailing newline). `--check` writes nothing; it exits non-zero
and prints a diff when a committed catalog differs from what it would generate. CI runs
`--check`. Nobody edits a catalog by hand.

## 7. Skills

Each skill is a directory `plugins/<plugin>/skills/<skill>/` containing:

| File | Required | Purpose |
| --- | --- | --- |
| `SKILL.md` | yes | Frontmatter + instructions, per the [Agent Skills specification](https://agentskills.io/specification) |
| `README.md` | no | Human documentation: when it triggers, before/after examples. Shown on the site. |
| `evals/*.eval.yaml` | no (expected) | `skill-lens` eval cases. Discovered by `skill-lens` from the `evals/` directory beside `SKILL.md`. |
| `scripts/`, `references/`, `assets/` | no | Per the Agent Skills specification |

Frontmatter rules (Agent Skills specification, enforced by `skills-ref validate`):

- `name`: 1–64 characters, `a-z`, `0-9` and single hyphens, no leading or trailing hyphen,
  **equal to the directory name**.
- `description`: 1–1024 characters, says what the skill does **and** when to use it.
- `license: MIT` on every skill in this repository (repository rule).
- `compatibility` (≤ 500 characters), `metadata` (string → string), `allowed-tools` only when
  needed.

Repository rules on top of the specification (enforced by tests, §9.1):

- A skill name is unique across **all** plugins.
- `SKILL.md` exists only at `plugins/*/skills/*/SKILL.md` — never deeper, never elsewhere.
- `SKILL.md` stays under 500 lines (the specification's recommendation); longer material
  moves into `references/`.
- Links in a skill's `README.md` are absolute URLs. A relative link would break on the site,
  and `mkdocs build --strict` fails the build when it does.

## 8. Landing page and documentation site

### 8.1 `README.md` — the landing page

Short, as in `skill-evaluator`: what the repository is (one paragraph), the list of plugins
(names and one-line descriptions — not every skill), an install block per tool, a link to the
site, and the license. No reference prose lives in the README. A test fails when a plugin is
missing from it.

### 8.2 The site

MkDocs with the Material theme, published at `https://emadmokhtar.github.io/agents-skills/`.

```
docs/
  index.md           what this is, why, how it is organised; the catalog table is appended at build time
  install.md         one tab per tool (Claude Code, Copilot CLI, VS Code, Codex, Cursor via npx skills)
  contributing.md    add a skill or plugin, the checks, evals, releases, one-time repository settings
  roadmap.md
  adr/
    README.md
    0001-one-plugin-per-category.md
    0002-agent-plugins-standard-with-generated-catalogs.md
    0003-release-please-per-plugin.md
    template.md      excluded from the site
  superpowers/       excluded from the site; historical specs and plans
```

Navigation: Home, Install, Skills (generated), Contributing, Decisions, Roadmap.

Configuration follows `pyfr/mkdocs.yml`: `validation` set so `--strict` fails on broken
links and anchors; `exclude_docs` for `superpowers/` and `adr/template.md`; Material features
`navigation.sections`, `navigation.top`, `content.code.copy`, `content.action.edit`,
`search.highlight`, `toc.follow`; light/dark palette; extensions `admonition`, `attr_list`,
`tables`, `toc` (permalinks), `pymdownx.details`, `pymdownx.superfences`,
`pymdownx.tabbed` (alternate style), `pymdownx.snippets` (`check_paths: true`).

### 8.3 Generated skill pages

Two MkDocs plugins do the generation. Both are by the same author and are commonly used
together:

- `mkdocs-gen-files` runs `scripts/gen_skill_pages.py` during `mkdocs build` and
  `mkdocs serve`, creating pages in memory. Nothing generated is committed, so nothing drifts.
- `mkdocs-literate-nav` builds the Skills navigation from a generated `skills/SUMMARY.md`.

The script produces:

| Page | Content |
| --- | --- |
| `skills/index.md` | Catalog: every plugin, its skills, one-line descriptions |
| `skills/<plugin>/index.md` | Plugin description, install commands per tool, list of its skills |
| `skills/<plugin>/<skill>.md` | Description; install and invoke commands per tool (tabs); `compatibility` and `allowed-tools` when present; the skill's `README.md`; a collapsed block "What the agent reads" containing the raw `SKILL.md` in a fenced code block; a link to the source on GitHub |
| `index.md` (appended) | The catalog table, added after the hand-written introduction |

Each generated page sets its edit link to the source file (`SKILL.md` or `README.md`), so
"Edit this page" opens the file a contributor actually changes.

### 8.4 Publishing

`.github/workflows/docs.yml`, as in `skill-evaluator`: on push to `main` and on manual
trigger; `build` job runs `uv sync --group docs` and `mkdocs build --strict`, then
`actions/upload-pages-artifact`; `deploy` job runs `actions/deploy-pages`. No `gh-pages`
branch. Workflow-level `permissions: {}`; each job asks for what it uses. Pull requests do not
deploy; CI builds the site instead (§9.1).

## 9. Checks

### 9.1 Free checks — every pull request and every push to `main` (`ci.yml`)

The same set runs locally with `just check`. None of them calls a model or needs a secret.

| Check | Command / tool | Catches |
| --- | --- | --- |
| Manifest schema | `check-jsonschema --schemafile schemas/agent-plugins/1.0.0/plugin.schema.json plugins/*/plugin.json` | unknown fields, bad names, missing `$schema` |
| Skill format | `agentskills validate <skill-dir>` (from the `skills-ref` package) for every skill | frontmatter violations, name ≠ directory |
| Claude Code view | `claude plugin validate --strict .` and on each `plugins/<plugin>` (locally, `just check` prints a visible warning and skips this row when `claude` is not on `PATH`; CI always runs it) | anything Claude Code would warn about at install |
| Catalogs in sync | `scripts/sync_catalogs.py --check` | hand-edited or stale catalogs |
| Repository rules | `pytest` (§9.2) | the rules no external tool knows |
| Eval files valid | `skill-lens list` over the skills | broken eval YAML — no model is called |
| Docs build | `mkdocs build --strict` | broken navigation, links, anchors, includes |
| Python lint | `ruff check` and `ruff format --check` on `scripts/` and `tests/` | style and simple bugs |
| PR title | `amannn/action-semantic-pull-request` | a non-conventional squash commit on `main` |

### 9.2 Repository rules (pytest)

- every directory under `plugins/` has a `plugin.json`, and its `name` equals the directory
  name and matches the `emad-` pattern;
- every skill directory sits exactly at `plugins/*/skills/*/` and has a `SKILL.md`; no
  `SKILL.md` exists anywhere else (test fixtures excepted);
- skill names are unique across all plugins;
- `SKILL.md` has `license: MIT` and is under 500 lines;
- every plugin appears in `README.md`;
- every plugin is registered in `release-please-config.json` and
  `.release-please-manifest.json`, and the manifest version equals `plugin.json` `version`;
- unit tests for `sync_catalogs.py`, `gen_skill_pages.py`, `new_plugin.py`, `new_skill.py`.

### 9.3 Real evaluations (`evals.yml`) — opt-in

- Triggers: manual (`workflow_dispatch`, input: a skill path or "all"), and pull requests
  that carry the label `run-evals`.
- On a pull request, only the skills the pull request changed are evaluated. A skill counts
  as changed when any file under its directory changed, including its eval files.
- Runs the `EmadMokhtar/skill-evaluator` action, pinned by commit SHA, with
  `runner: claude-code` (and `judge = "claude-code"` for rubric cases). Claude Code is
  installed in the job. It authenticates with the `CLAUDE_CODE_OAUTH_TOKEN` secret.
- Hardening, from the skill-lens CI documentation: `allow-scripts: false` set explicitly,
  `actions/checkout` with `persist-credentials: false`, job permissions `contents: read`
  only.
- A fork's pull request has no access to the secret, so the job fails at the missing token.
  This is acceptable: the label is applied by the maintainer.

Locally: `just eval <plugin>/<skill>` runs `skill-lens run` with `--runner claude-code`
through the installed Claude Code. No API key is needed.

### 9.4 Repository hygiene

- Every third-party action is pinned by commit SHA with the version in a comment.
- Workflows declare `permissions: {}` at the top; each job asks for exactly what it uses.
- Dependabot updates GitHub Actions and `uv` dependencies.
- `.pre-commit-config.yaml`: JSON/YAML syntax, end-of-file and trailing-whitespace fixers,
  `ruff`, and `sync_catalogs.py --check`.
- `.github/pull_request_template.md`: Conventional Commits title reminder, documentation
  checkbox, "evals run?" checkbox for skill changes.
- `.github/copilot-instructions.md` (repository-wide rules) and
  `.github/instructions/skills.instructions.md` (`applyTo: plugins/**`) and
  `.github/instructions/docs.instructions.md` (`applyTo: docs/**, mkdocs.yml, *.md`).
- `AGENTS.md` holds the agent working rules (Codex and Copilot read it). `CLAUDE.md` contains
  only `@AGENTS.md`, Claude Code's import syntax, so the rules exist once.

## 10. Releases

release-please in manifest mode.

- `release-please-config.json` has one package per plugin (`plugins/emad-coding`), with
  `separate-pull-requests: true`, `bump-minor-pre-major: true`, tag format
  `<plugin>-v<version>` (for example `emad-coding-v0.2.0`), and an `extra-files` JSON
  updater for `plugin.json` at `$.version`.
- `.release-please-manifest.json` holds the current version of each plugin. Plugins start at
  `0.0.0`, which means "not released yet", so the first `feat` release is `0.1.0`. (Changed
  during planning: starting at `0.1.0` would make the first `feat` merge release `0.2.0`.)
- Bump rules come from Conventional Commits: `fix` → patch, `feat` → minor, `!` or
  `BREAKING CHANGE:` → major (minor while below 1.0). release-please decides **which plugin**
  a commit belongs to from the paths it touches, not from the scope. A scope such as
  `feat(emad-coding): …` is still good practice for readers.
- Merging a plugin's release pull request bumps `plugin.json`, writes
  `plugins/<plugin>/CHANGELOG.md` (the specification's standard layout already lists a
  `CHANGELOG.md` at the plugin root), creates the tag, and publishes a GitHub Release.
- `.github/workflows/release.yml` runs on push to `main` and uses the
  `RELEASE_PLEASE_TOKEN` secret. Reason: a pull request opened with the default
  `GITHUB_TOKEN` does not trigger other workflows, so CI would never run on release pull
  requests. The token is a fine-grained personal access token scoped to this repository only,
  with Contents and Pull requests set to read/write.

This differs from `skill-evaluator` and `pyfr`, which bump and tag directly on `main`
without a release pull request. ADR 0003 records why: several independently versioned
plugins in one repository is the case release-please's manifest mode exists for.

## 11. Scaffolding

- `just new-plugin <name>` → `scripts/new_plugin.py`: validates the name (`emad-` pattern),
  creates `plugins/<name>/plugin.json` at `0.1.0` and `skills/`, registers it in both
  release-please files, runs `sync_catalogs.py`, and reminds the author to add a README line.
- `just new-skill <plugin> <name>` → `scripts/new_skill.py`: validates the name and its
  repository-wide uniqueness, creates `SKILL.md` (frontmatter filled in, body outline),
  `README.md`, and `evals/<name>.eval.yaml` with one placeholder case.

## 12. The example skill: `emad-coding:conventional-commits`

Purpose: prove the whole pipeline (install, docs page, checks, evals, release) with a skill
Emad uses every day.

- `SKILL.md` encodes the Conventional Commits rules from Emad's global `CLAUDE.md`:
  - format `<type>[optional scope][!]: <description>`;
  - types `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`,
    `style`, `revert`;
  - description in the imperative mood, lowercase, no trailing period;
  - breaking changes: `!` after the type or scope, and/or a `BREAKING CHANGE:` footer;
  - the optional body explains *why*, not *what*;
  - pull request titles follow the same format, because a squash merge turns the title into
    the commit on `main`;
  - never a bare summary such as `Update auth`.
- The skill applies when writing a commit message, a pull request title, or reviewing one.
- `README.md`: when it triggers, before/after examples.
- `evals/conventional-commits.eval.yaml`: four cases — a new feature, a bug fix, a breaking
  change, and rewriting the bad title `Update auth`. Assertions check the format with a
  regular expression and the absence of a trailing period. The exact assertion kinds are
  confirmed against the skill-lens eval-file reference during planning.

## 13. Open items — resolved during planning (2026-10-05)

1. `skill-lens list plugins` finds nested skills at any depth. `list` and `run` take **one**
   path each, so CI runs one matrix job per skill.
2. release-please `simple` only logs "file version.txt did not exist" and never creates it.
   A JSON `extra-files` updater bumps `plugin.json`. Do not set `version-file`, because it
   would overwrite `plugin.json` with a bare version string.
3. `claude plugin validate` works without a login (tested with an empty environment). Pin
   `@anthropic-ai/claude-code@2.1.289`, which needs Node 22+. A plugin *folder* check reads
   the skills but not a root `plugin.json`, so CI also validates each `plugin.json` by path.
4. Codex: `category` is free text, and `interface` is optional. `policy.installation` is one
   of `AVAILABLE`, `NOT_AVAILABLE`, `INSTALLED_BY_DEFAULT`. `policy.authentication` is one of
   `ON_INSTALL`, `ON_USE`.
5. `mkdocs-gen-files` can append to `docs/index.md` inside the build only; the file on disk
   is not changed. Both MkDocs plugins pull in `properdocs`, which prints a notice unless
   `DISABLE_MKDOCS_2_WARNING=true`.
6. `skills-ref` 0.1.1 installs a command named `agentskills`. `agentskills validate <dir>`
   takes one folder per call. Its parser is strict YAML: unquoted `: ` in a value and
   `[a, b]` lists fail.
7. skill-lens 0.20.0 assertion kinds: `contains`, `not_contains`, `regex`, `equals`,
   `file-produced`, `json-schema`. "First line does not end with a period" is the regex
   `\A(?![^\n]*\.[ \t]*(?:\n|\Z))`. Eval cases use `task:`, not `prompt:`.

Also found: skill-lens's `claude-code` runner starts Claude Code with
`--dangerously-skip-permissions`. The `run-evals` label must only go on a pull request the
maintainer has read (§9.3).

## 14. One-time manual repository settings

Documented in `docs/contributing.md`:

- Settings → Pages → Source = "GitHub Actions" (the first deploy fails until this is set).
- Secrets: `RELEASE_PLEASE_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` (created with
  `claude setup-token`).
- Label: `run-evals`.
- Branch protection on `main`: require the CI checks and a Conventional Commits PR title;
  squash merge only.
- Copilot code review enabled for the repository.

## 15. Out of scope

- The repository-initialisation skill (the next spec).
- Moving Emad's existing skills into this repository.
- A Cursor catalog (`.cursor-plugin/marketplace.json`).
- MCP servers (`mcp.json`).
- Versioned documentation.
- Moving the site from MkDocs Material to Zensical.

## 16. Glossary

| Term | Meaning |
| --- | --- |
| ADR | Architecture Decision Record — a short file recording one decision and why it was made. |
| Agent Plugins | An open standard (v1.0.0) for packaging skills and MCP servers so many agent tools can load them. |
| Agent Skills | The open `SKILL.md` format: a folder with instructions an agent loads on demand. |
| Catalog / marketplace file | A JSON file at the repository root that lists the plugins inside it, so a tool can offer them for install. |
| CI | Continuous integration — checks that run automatically on every pull request and push. |
| Closed schema | A JSON schema that rejects any field it does not list. |
| Conventional Commits | A commit message format (`type(scope): description`) that tools can read to decide versions. |
| MCP | Model Context Protocol — a standard way for an agent to call external tools and data sources. |
| PAT | Personal access token — a GitHub token that acts as a user, with permissions you choose. |
| release-please | A GitHub Action that reads Conventional Commits and opens a pull request that bumps versions and writes the changelog. |
| skill-lens | Emad's tool (repository `skill-evaluator`) that runs evaluation cases against a skill. |
| YAGNI | "You aren't gonna need it" — do not build something until it is actually needed. |

# Contributing

## Set up

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), and Node.js 22 or
later with Claude Code (`npm install --global @anthropic-ai/claude-code`).

```bash
just install                  # every dependency group
uv run pre-commit install     # run the quick checks before each commit
```

## The checks

`just check` runs every free check, exactly as CI does. None of them calls a model.

| Recipe | What it checks |
| --- | --- |
| `just lint` | ruff on the Python code, actionlint on the workflows |
| `just test` | pytest |
| `just layout` | repository rules: names, placement, unique skill names, release registration, README |
| `just manifests` | each `plugin.json` against the stored Agent Plugins 1.0.0 schema |
| `just skills` | each `SKILL.md` against the Agent Skills specification (`agentskills validate`) |
| `just catalogs` | the two catalog files match the `plugin.json` files |
| `just evals-list` | every eval file is valid (`skill-lens list`) |
| `just claude-validate` | the marketplace and plugins the way Claude Code reads them |
| `just docs-build` | the site builds with `--strict` |

If `claude` is not installed, `just claude-validate` prints a warning and skips. CI always
runs it.

## Add a skill

```bash
just new-skill emad-coding <skill-name>
```

This creates `SKILL.md`, `README.md` and one placeholder eval case. Then:

1. **Write the description.** It says what the skill does *and* when to use it, in at most
   1024 characters. `just layout` fails while it still starts with `TODO`.
2. **Write the body.** Keep `SKILL.md` under 500 lines. Move long reference material into
   `references/`.
3. **Use strict YAML in the frontmatter.** Quote any value that contains `: `, or use a
   folded block (`description: >-`). Write lists as one item per line, never `[a, b]`.
4. **Write `README.md` for people.** It is shown on this site. Use absolute links only. A
   relative link breaks the site build.
5. **Write real eval cases** in `evals/`. See [Evals](#evals).

Skill names must be unique across **all** plugins, because `npx skills` installs every
skill into one folder.

## Add a plugin (a new category)

```bash
just new-plugin emad-jobs "Job search skills: cover letters, outreach, and more."
```

This writes `plugins/emad-jobs/plugin.json` at version `0.0.0` ("not released yet"). It also
registers the plugin with release-please and regenerates both catalogs. Then:

1. Add the plugin to the table in `README.md`.
2. Add its first skill with `just new-skill`. A plugin without skills fails `just layout`.

Never edit `.claude-plugin/marketplace.json` or `.agents/plugins/marketplace.json` by hand.
Change `plugin.json` and run `just sync`.

## Evals

Eval cases are YAML files in a skill's `evals/` folder, in the
[skill-lens](https://emadmokhtar.github.io/skill-evaluator/) format. Each case has a `name`, a
`task` and `assertions`. The assertion kinds are `contains`, `not_contains`, `regex`,
`equals`, `file-produced` and `json-schema`.

Run them for real through your installed Claude Code. This uses your Claude quota but needs
no API key:

```bash
just eval emad-coding/conventional-commits
```

In CI, real evals run only when started by hand (**Actions → Evals → Run workflow**), or
when a pull request has the `run-evals` label. Then only the skills that the pull request
changed are evaluated.

!!! danger "Read a pull request before you add `run-evals`"
    skill-lens starts Claude Code with `--dangerously-skip-permissions`. A `SKILL.md` in a
    pull request could tell Claude to read the `CLAUDE_CODE_OAUTH_TOKEN` secret and send it
    somewhere. Pull requests from forks get no secrets, so for them the job simply fails.

## Commits and pull request titles

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for every commit
and every pull request title. Pull requests are squash-merged, so the title becomes the
commit on `main`.

A change to what a skill does is `feat` or `fix`, even though the file is Markdown.
release-please hides `docs`, `chore`, `refactor`, `test`, `build`, `ci` and `style`, so a
skill change committed as `docs:` is never released.

## Releases

[release-please](https://github.com/googleapis/release-please) versions each plugin on its
own.

1. Merge a `feat` or `fix` change under `plugins/<plugin>/`.
2. release-please opens or updates a pull request titled
   `chore(main): release <plugin> <version>`.
3. Merge that pull request. It bumps `version` in `plugin.json`, writes
   `plugins/<plugin>/CHANGELOG.md`, tags `<plugin>-v<version>`, and publishes a GitHub
   Release.

The config sets `initial-version: 0.1.0`, so a plugin's first release is `0.1.0`, not `1.0.0`.
`just check` fails if that key is missing.

release-please picks the plugin from the paths a commit touches, not from its scope. Its log
always warns that `version.txt` does not exist. That warning is expected: this repository
keeps the version in `plugin.json`.

## One-time repository settings

These cannot be set from a file:

- **Settings → Pages → Source = GitHub Actions.** The first docs deploy fails until this is
  set.
- **Secret `RELEASE_PLEASE_TOKEN`:** a fine-grained personal access token for this repository
  only, with *Contents*, *Issues* and *Pull requests* set to read and write. release-please
  manages its `autorelease:` labels through the issues API, so it needs *Issues*. A pull
  request opened with the default `GITHUB_TOKEN` does not trigger CI, so the release pull
  request could never pass its checks.
- **Secret `CLAUDE_CODE_OAUTH_TOKEN`:** create it with `claude setup-token`. Used only by the
  Evals workflow.
- **Label `run-evals`.**
- **Branch protection on `main`:** require the `checks` and `pr-title` jobs, and allow squash
  merge only.
- **Copilot code review:** turn it on for the repository, so it reads
  `.github/copilot-instructions.md` and `.github/instructions/`.

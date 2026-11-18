# Agent instructions

This repository holds Emad Mokhtar's agent skills, packaged as Agent Plugins 1.0.0
(https://agent-plugins.org/specification), with one plugin per category.

## Layout rules

- Each plugin is `plugins/emad-<category>/` with a root `plugin.json`. Edit only that file.
  `just sync` copies it to the plugin's `.claude-plugin/plugin.json`, which the Claude app
  needs. Never edit that copy by hand.
- Each skill is `plugins/<plugin>/skills/<skill>/SKILL.md`: exactly one level under `skills/`,
  never deeper.
- Skill names are unique across all plugins.
- `plugin.json` has no `extensions` and no `author.email`. `version` lives only in
  `plugin.json`, its generated `.claude-plugin/plugin.json` copy, and
  `.release-please-manifest.json`. release-please bumps all three.
- Never edit `.claude-plugin/marketplace.json` or `.agents/plugins/marketplace.json` by hand.
  Run `just sync`.
- Create plugins and skills with `just new-plugin` and `just new-skill`, never by hand.

## Writing skills

- Frontmatter: `name` equals the folder name. `description` says what the skill does and when
  to use it (at most 1024 characters). Add `license: MIT`.
- Frontmatter is strict YAML: quote values that contain `: `, and never use `[a, b]` lists.
- Keep `SKILL.md` under 500 lines. Put long material in `references/`.
- `README.md` in a skill folder is for people and is shown on the site. Use absolute links.
- Add or update eval cases in `evals/` whenever the skill's behaviour changes.

## Running evals and checks locally

- `secret run CLAUDE_CODE_OAUTH_TOKEN -- just eval emad-jobs/job-scout` runs one skill's
  evals. skill-lens gives Claude Code a temporary home (`product_sandbox = "auto"`), so it
  cannot see the normal login. Without the token, every skill exits 2 before any case runs.
  `secret` reads the token from the keychain and never prints it.
- Never pass `--product-sandbox off` or set `product_sandbox = "off"` to avoid the token.
  "off" gives Claude Code, started with `--dangerously-skip-permissions`, the real home
  folder.
- Never print the token, or write it into chat or a file.
- In a new worktree, run `just install` before `just check`. Plain `uv run` skips the `docs`
  group, so `just docs-build` fails with "Failed to spawn: mkdocs".

## Before you finish

- Run `just check`. It must pass.
- Documentation ships in the same change: `docs/` for people, `README.md` when a plugin is
  added.
- Commit messages and pull request titles follow Conventional Commits. A change to a skill's
  behaviour is `feat` or `fix`, never `docs`. Otherwise release-please does not release it.
- Never add the `run-evals` label to a pull request you have not read. The eval runner starts
  Claude Code with `--dangerously-skip-permissions`.
- Write comments, docs and commit messages in simple, direct English.

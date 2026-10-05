# Copilot review instructions

This repository packages Agent Skills as Agent Plugins 1.0.0, one plugin per category under
`plugins/emad-<category>/`. Read `AGENTS.md` for the full rules.

When reviewing a pull request, flag:

- a `SKILL.md` that is not exactly at `plugins/<plugin>/skills/<skill>/SKILL.md`;
- a skill name already used by another plugin;
- a hand edit to `.claude-plugin/marketplace.json` or `.agents/plugins/marketplace.json`
  without the matching `plugin.json` change;
- `extensions`, `author.email`, or a `.claude-plugin/plugin.json` file inside a plugin;
- a `version` change outside a release-please pull request;
- a pull request title that is not a Conventional Commit, or a skill behaviour change titled
  `docs:` (release-please does not release `docs`);
- a GitHub Action not pinned by full commit SHA, or a workflow without `permissions: {}`;
- a skill behaviour change without eval cases that cover it;
- relative links in a skill's `README.md`.

Do not suggest: adding a `skills` field to `plugin.json` (the schema is closed), nesting
skills deeper than one level, or removing `--strict` from any check.

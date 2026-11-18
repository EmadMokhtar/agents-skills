# 0004. Generate a Claude manifest in every plugin

**Status:** Accepted
**Date:** 2026-11-18

## Context

[ADR 0002](0002-agent-plugins-standard-with-generated-catalogs.md) kept only the root
`plugin.json` in each plugin. That works in Claude Code: the terminal app installs a plugin
from its catalog entry, without `.claude-plugin/plugin.json`.

The Claude app (claude.ai, Claude Desktop, Cowork) is stricter. Anthropic's
[plugin docs](https://claude.com/docs/plugins/build) say a plugin folder has its manifest at
`.claude-plugin/plugin.json`. They also say a plugin without any `plugin.json` is listed "for
Claude Code only, not for claude.ai or Cowork". A user who added this marketplace in the app
got a sync error. The error text did not name a cause. The user's Claude rebuilt `emad-jobs`
as an uploaded `.plugin` file, with the manifest moved to `.claude-plugin/plugin.json`.

ADR 0002 rejected a `.claude-plugin/plugin.json` copy for two reasons: it duplicates the
manifest, and the standard's `extensions` field made `claude plugin validate --strict` fail.
This repository has since banned `extensions` (`just layout` reports it), so only the first
reason is left.

## Decision

`just sync` writes `plugins/<plugin>/.claude-plugin/plugin.json` from the root `plugin.json`.
The copy keeps every field and its order, except `$schema`, because that URL names the Agent
Plugins schema, not Claude's. `just catalogs` fails in CI when a copy differs from what
`just sync` would write. release-please bumps `version` in both files, and `just layout`
checks that every plugin's release config does this.

## Alternatives considered

- **Move the manifest into `.claude-plugin/` only.** Rejected: Codex, GitHub Copilot and
  VS Code read the root `plugin.json`, as the Agent Plugins standard says.
- **A hand-written copy.** Rejected: two hand-edited files drift apart.
- **A copy without `version`.** Rejected: Claude Code reads this file when it exists. Without
  a version, it treats each commit as a new version.
- **Ask app users to upload a `.plugin` file.** Rejected: an uploaded plugin never gets
  updates from this repository.

## Consequences

- The Claude app can add this repository as a marketplace and install its plugins.
- Each plugin has two manifest files. People edit only the root `plugin.json`.
- Every release-please package needs two `extra-files` entries. `just new-plugin` writes
  both.
- ADR 0002's concern that Claude Code reads `version` from the root `plugin.json` without
  documentation no longer applies. Claude Code now reads the documented file.

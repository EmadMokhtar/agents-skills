# 0002. Follow Agent Plugins, and generate the client catalogs

**Status:** Accepted
**Date:** 2026-10-05

## Context

Agent Plugins 1.0.0 puts the manifest at the plugin root, in `plugin.json`. Codex, GitHub
Copilot, VS Code and Cursor read that file. Claude Code is not on the standard's list of
compatible clients: it reads `.claude-plugin/plugin.json`, and it finds plugins through
`.claude-plugin/marketplace.json`. Copilot, VS Code and `npx skills` also read
`.claude-plugin/marketplace.json`. The Codex documentation names
`.agents/plugins/marketplace.json`. When a plugin also carries a `.claude-plugin/plugin.json`
copy, `claude plugin validate --strict` fails on the standard's `extensions` field. Without
the copy, Claude Code installs the plugin correctly from its catalog entry.

## Decision

Each plugin has only the standard root `plugin.json`. `scripts/sync_catalogs.py` generates
`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` from those manifests,
and CI fails when the committed catalogs differ from the generated ones. The version lives
only in `plugin.json`.

## Alternatives considered

- **A `.claude-plugin/plugin.json` copy in every plugin.** Rejected: it duplicates the
  manifest, and the `extensions` field makes `--strict` validation fail.
- **Hand-written catalogs.** Rejected: three files describing the same plugins drift apart.
- **A Cursor catalog (`.cursor-plugin/marketplace.json`).** Deferred: Cursor reads it only
  for its own marketplace and for Team plans. `npx skills` covers Cursor users today.

## Consequences

- `plugin.json` is the single source of truth. `just sync` updates everything else.
- Claude Code was observed reading `version` from the root `plugin.json`, but this is not
  documented. If it stops, Claude Code treats each commit as a new version. Installs still
  work.
- Cursor users install single skills through `npx skills`.

# 0001. Make each category its own plugin

**Status:** Accepted
**Date:** 2026-10-05

## Context

Emad wants all of his skills in one repository, grouped by category, such as job search or
coding. The repository follows Agent Plugins 1.0.0. Section 7.1 of that standard discovers
skills only at `skills/<name>/SKILL.md`, and says clients "MUST NOT recursively search deeper
descendants". The manifest schema is closed and has no field that points at other skill
folders. A layout like `skills/jobs/<skill>/` inside one plugin is therefore invisible to
every conformant client.

## Decision

We make each category its own plugin, at `plugins/emad-<category>/`, with its skills at
`plugins/emad-<category>/skills/<skill>/`. The category folder still groups the skills, and
the layout is fully standard.

## Alternatives considered

- **One plugin with a flat `skills/` folder, and the category as metadata.** Rejected: the
  folders are not grouped, and one install always brings every skill.
- **Grouped source folders, plus a generated flat `skills/` folder.** Rejected: every skill
  exists twice, and a check must keep the copies equal.
- **Claude Code's `skills` array in `.claude-plugin/plugin.json`.** Rejected: it is not part
  of Agent Plugins, so every other client ignores it.

## Consequences

- People install only the categories they want.
- Commands carry the plugin name: `/emad-coding:conventional-commits`.
- Skill names must be unique across all plugins, because `npx skills` installs every skill
  into one folder.
- A new category is a new plugin, with its own version and changelog.

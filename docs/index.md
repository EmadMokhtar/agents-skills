# Emad's agent skills

Agent skills by Emad Mokhtar, packaged as [Agent Plugins](https://agent-plugins.org/).
Each category of skills is one plugin, so you install only the categories you want.

A **skill** is a folder with a `SKILL.md` file. It holds instructions an agent loads when a
task needs them ([Agent Skills format](https://agentskills.io/specification)). A **plugin**
is a folder with a `plugin.json` manifest and a `skills/` folder
([Agent Plugins 1.0.0](https://agent-plugins.org/specification)).

## Works with

Claude Code, GitHub Copilot (CLI and VS Code), OpenAI Codex, and Cursor or any other tool
that reads `SKILL.md`, through [`npx skills`](https://github.com/vercel-labs/skills). See
[Install](install.md).

## How the repository is organised

```text
plugins/
  emad-<category>/
    plugin.json          the plugin manifest
    skills/
      <skill>/
        SKILL.md         what the agent reads
        README.md        what people read (shown on this site)
        evals/           skill-lens test cases
```

Skill names are unique across all plugins, so you can also install one skill on its own.

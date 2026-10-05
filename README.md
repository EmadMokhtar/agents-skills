# agents-skills

Agent skills by Emad Mokhtar, packaged as [Agent Plugins](https://agent-plugins.org/), with
one plugin per category. They work in Claude Code, GitHub Copilot, VS Code, OpenAI Codex,
Cursor, and any tool that reads `SKILL.md`.

**Documentation:** <https://emadmokhtar.github.io/agents-skills/>

## Plugins

| Plugin | What it covers |
| --- | --- |
| [`emad-coding`](https://emadmokhtar.github.io/agents-skills/skills/emad-coding/) | Coding workflow skills: commit messages, pull request titles, and more. |

## Install

Claude Code:

```text
/plugin marketplace add EmadMokhtar/agents-skills
/plugin install emad-coding@emad-skills
```

GitHub Copilot CLI:

```bash
copilot plugin install EmadMokhtar/agents-skills:plugins/emad-coding
```

OpenAI Codex:

```bash
codex plugin marketplace add EmadMokhtar/agents-skills
```

Cursor and other tools:

```bash
npx skills add EmadMokhtar/agents-skills --skill conventional-commits -a cursor
```

Every option, including VS Code, is in the
[install guide](https://emadmokhtar.github.io/agents-skills/install/).

## Contributing

See the [contributing guide](https://emadmokhtar.github.io/agents-skills/contributing/).

## License

[MIT](LICENSE)

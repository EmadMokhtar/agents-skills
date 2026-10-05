# Install

Pick your tool. Every plugin is named `emad-<category>`. The [catalog](skills/index.md)
shows what each one contains.

!!! warning "Use one install method per tool"
    If you install the same skill both as a plugin and through `npx skills`, your tool gets
    two copies of it.

## Claude Code

Add the marketplace once, then install the plugins you want:

```text
/plugin marketplace add EmadMokhtar/agents-skills
/plugin install emad-coding@emad-skills
```

From a terminal, the same commands are `claude plugin marketplace add ...` and
`claude plugin install ...`. A skill's command is `/<plugin>:<skill>`, for example
`/emad-coding:conventional-commits`. Claude also loads a skill by itself when a task matches
its description.

## GitHub Copilot CLI

Install one plugin straight from its folder:

```bash
copilot plugin install EmadMokhtar/agents-skills:plugins/emad-coding
```

Or add the marketplace and install by name:

```bash
copilot plugin marketplace add EmadMokhtar/agents-skills
copilot plugin install emad-coding@emad-skills
```

## VS Code

Run **Chat: Install Plugin From Source** from the Command Palette, and paste
`https://github.com/EmadMokhtar/agents-skills`.

To browse every plugin in the Extensions view (search for `@agentPlugins`), add the
repository to your settings:

```json
"chat.plugins.marketplaces": ["EmadMokhtar/agents-skills"]
```

## OpenAI Codex

```bash
codex plugin marketplace add EmadMokhtar/agents-skills
```

Then open `/plugins` in Codex and install the plugin you want.

## Cursor and other tools

Cursor documents no way to install a plugin straight from GitHub on every plan, so use
[`npx skills`](https://github.com/vercel-labs/skills). It copies skills into the folder your
tool reads:

```bash
npx skills add EmadMokhtar/agents-skills --skill conventional-commits -a cursor
```

Leave out `--skill` to choose from a list. Change `-a` for another tool, for example
`-a codex` or `-a claude-code`. Add `--list` to see every skill without installing anything.

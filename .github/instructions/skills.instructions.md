---
applyTo: "plugins/**"
---

# Skills and plugins

- `SKILL.md` frontmatter must be strict YAML: quoted values when they contain `: `, block
  lists only. `name` equals the folder name. `license: MIT` is required.
- The description must say what the skill does and when to use it. Flag vague descriptions
  such as "Helps with X".
- `SKILL.md` stays under 500 lines. Long material belongs in `references/`.
- A change to the instructions needs a matching change in `evals/`. Assertions must test
  behaviour, not wording that is likely to vary.
- `plugin.json` changes must keep the Agent Plugins 1.0.0 schema: no unknown fields, no
  `extensions`, no `author.email`.

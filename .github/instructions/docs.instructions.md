---
applyTo: "docs/**,mkdocs.yml,README.md"
---

# Documentation

- `README.md` is a landing page: what the repository is, the plugin table, short install
  commands, links. Reference material belongs on the site under `docs/`.
- A new page must be added to `nav` in `mkdocs.yml`. The Skills section is generated: never
  add files under `docs/skills/`.
- Decision records in `docs/adr/` are never edited after acceptance. A changed decision is a
  new record.
- Write in simple, direct English: short sentences, no idioms, every acronym expanded on
  first use.

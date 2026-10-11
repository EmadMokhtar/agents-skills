# Roadmap

## Done

- The repository: one Agent Plugin per category, generated catalogs for Claude Code and
  Codex, this site, free CI checks, opt-in evals, and per-plugin releases.
- First skill: [`conventional-commits`](skills/emad-coding/conventional-commits.md) in
  `emad-coding`.
- [`hiring-contact-finder`](skills/emad-jobs/hiring-contact-finder.md) in `emad-jobs`: finds the
  hiring manager or recruiter behind a job post and drafts a short, professional message.
- [`repo-setup`](skills/emad-coding/repo-setup.md) in `emad-coding`: sets up or completes a
  repository the way PyFR is set up, for any language: Conventional Commits, one `just check`
  recipe for CI, a documentation site, releases with commitizen, Dependabot, security scans, and
  a checklist of one-time GitHub settings.

## Next

- Language packs for `repo-setup`: the lint and test jobs for Python, Go and Node, added to
  the `check` recipe on request.
- Move Emad's existing skills into this repository, starting with `writing-skill-evals` from
  [skill-evaluator](https://github.com/EmadMokhtar/skill-evaluator).

## Later, only when needed

- A Cursor catalog (`.cursor-plugin/marketplace.json`), if someone needs the Cursor
  Marketplace.
- MCP servers (`mcp.json`), when a skill needs one.
- Moving the site from MkDocs Material to its successor, Zensical, together with Emad's
  other projects.

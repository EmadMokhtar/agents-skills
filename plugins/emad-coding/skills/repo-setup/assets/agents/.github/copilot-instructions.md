# Copilot review instructions

__DESCRIPTION__ Read `AGENTS.md` for the full rules.

When reviewing a pull request, flag:

- a pull request title that is not a Conventional Commit, or a change to behaviour titled
  `docs:` or `chore:` (release automation does not release those types);
- a GitHub Action that is not pinned by full commit SHA, or a workflow without a
  `permissions:` block;
<!-- @if release -->
- a hand edit to `CHANGELOG.md`, or a hand edit of a version number (the release workflow
  writes both);
<!-- @endif -->
<!-- @if adr -->
- a change to a decision record in `docs/adr/` after it was accepted (a changed decision is a
  new record);
<!-- @endif -->
- a secret, token or key in the diff;
- a change to behaviour with no documentation change in the same pull request.

Do not suggest removing `--strict` from the documentation build, or `permissions: {}` from a
workflow.

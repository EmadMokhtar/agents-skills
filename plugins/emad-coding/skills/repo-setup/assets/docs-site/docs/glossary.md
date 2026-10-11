---
last_reviewed: __TODAY__
---

# Glossary

| Term | Meaning |
| --- | --- |
<!-- @if adr -->
| ADR | Architecture Decision Record. A one-page note that records a decision, why it was made, and what it costs. See [decision records](adr/README.md). |
<!-- @endif -->
<!-- @if release -->
| commitizen | The tool that checks commit messages, picks the next version from the commits since the last tag, writes the changelog, and tags the release. |
<!-- @else -->
| commitizen | The tool that checks that each commit message is a Conventional Commit. |
<!-- @endif -->
| Conventional Commits | A commit message format (`feat:`, `fix:`, `feat!:`) that a machine can read to choose a version number. |
| Dependabot | GitHub's service that opens a pull request when a dependency, an action or a hook has a newer version. |
| front matter | The block of settings between two `---` lines at the top of a page. Here it holds `last_reviewed` and `covers`. |
| GitHub Pages | GitHub's hosting for static sites. The Docs workflow publishes this site there. |
| just | A command runner. A `justfile` lists named recipes such as `just check`. |
<!-- @if uv -->
| pre-commit | A tool that runs checks (hooks) before each commit. |
<!-- @else -->
| Homebrew | A package manager for macOS and Linux. The install commands in this repository use it. |
| git hook | A script that git runs at a set moment, such as before a commit. The hooks live in `.githooks/`. |
<!-- @endif -->
| ruleset | A GitHub setting that protects a branch: it can require a pull request, require checks, and block force pushes. |
<!-- @if adr -->
| SHA pin | Naming an action by its full commit hash instead of a tag, so the code cannot change under us. See [ADR 0004](adr/0004-pin-actions-and-limit-permissions.md). |
<!-- @else -->
| SHA pin | Naming an action by its full commit hash instead of a tag, so the code cannot change under us. |
<!-- @endif -->
| squash merge | Merging a pull request as one commit. The pull request title becomes the commit message. |
<!-- @if uv -->
| uv | A fast Python package and tool manager. Here it installs the repository's tools. |
<!-- @endif -->
<!-- @if docs-gates -->
| `covers:` | Front matter key that lists the files a page describes. If one of them changes and the page does not, `just docs-freshness` warns. |
| lychee | A program that checks that the links in the documentation still work. |
| `last_reviewed` | Front matter key with the date someone last confirmed the page is true. |
<!-- @endif -->
<!-- @if security -->
| Trivy | A scanner for known vulnerabilities, secrets and bad configuration. |
<!-- @endif -->
<!-- @if container -->
| SBOM | Software bill of materials. The list of everything inside a piece of software. |
<!-- @endif -->

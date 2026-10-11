# __NAME__

__DESCRIPTION__

[![CI](https://github.com/__OWNER__/__SLUG__/actions/workflows/ci.yml/badge.svg)](https://github.com/__OWNER__/__SLUG__/actions/workflows/ci.yml)
<!-- @if licensed -->
[![License](https://img.shields.io/github/license/__OWNER__/__SLUG__)](LICENSE)
<!-- @endif -->
<!-- @if docs-site -->

**Documentation:** <__SITE_URL__>
<!-- @endif -->

## Get started

<!-- @if uv -->
You need [uv](https://docs.astral.sh/uv/) (installs the tools this repository uses) and
[just](https://just.systems/) (runs the repository's tasks).
<!-- @else -->
You need [just](https://just.systems/) (runs the repository's tasks) and a few small tools that
`just install` lists, with the command to install each one. The
[contributing guide](docs/contributing.md) has the table.
<!-- @endif -->

```bash
# @if uv
just install   # installs the tools and the git hooks
# @else
just install   # turns on the git hooks
# @endif
just check     # runs every check that CI runs
```

Run `just` to list every task.

## Contributing

Read the [contributing guide](docs/contributing.md). Commit messages and pull request titles
must follow [Conventional Commits](https://www.conventionalcommits.org/).
<!-- @if licensed -->

## License

[__LICENSE__](LICENSE)
<!-- @endif -->

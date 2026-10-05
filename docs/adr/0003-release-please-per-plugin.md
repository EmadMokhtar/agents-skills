# 0003. Version each plugin with release-please

**Status:** Accepted
**Date:** 2026-10-05

## Context

The repository holds several plugins, and each one changes on its own schedule. Emad's other
repositories bump one version per repository directly on `main` with Commitizen. Clients use
a plugin's `version` to decide when an update exists.

## Decision

We use release-please in manifest mode, with one package per plugin. Each package uses the
`simple` release type and a JSON updater for `plugin.json`. Each plugin gets its own release
pull request (`separate-pull-requests`) and tags of the form `<plugin>-v<version>`. The
workflow acts with a `RELEASE_PLEASE_TOKEN` personal access token, so CI runs on the release
pull requests. New plugins start at `0.0.0`, which means "not released yet". The config sets
`initial-version: 0.1.0`, so a plugin's first release is `0.1.0`.

## Alternatives considered

- **Commitizen, as in the other repositories.** Rejected: it gives one version for the whole
  repository.
- **No versions.** Rejected: there is no changelog, and every commit counts as an update.
- **semantic-release with monorepo plugins.** Rejected: it needs a Node.js toolchain and
  community plugins for a job release-please does natively.

## Consequences

- Each plugin has its own changelog and releases.
- A personal access token must be created and renewed.
- Without `initial-version`, release-please would make the first release `1.0.0`.
  `just check` fails if the key is missing.
- `docs`, `chore`, `refactor`, `test`, `build`, `ci` and `style` commits never release. A
  change to a skill's behaviour must be `feat` or `fix`.
- The `simple` release type logs a harmless warning that `version.txt` does not exist.

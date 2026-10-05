# conventional-commits

Writes and checks commit messages and pull request titles in the
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format.

## When it triggers

- You ask the agent to commit, or to write a commit message.
- You ask for a pull request title, or the agent opens a pull request.
- You ask whether a message or a title is correct.

## Before and after

| Before | After |
| --- | --- |
| `Update auth` | `fix(auth): reject expired tokens on refresh` |
| `Added login endpoint.` | `feat(api): add login endpoint` |
| `Remove v1 API` | `feat(api)!: remove v1 endpoints`, with a `BREAKING CHANGE:` footer |

## Why pull request titles matter

When a pull request is squash-merged, its title becomes the commit on the main branch.
Release tools such as [release-please](https://github.com/googleapis/release-please) read
that commit to choose the next version.

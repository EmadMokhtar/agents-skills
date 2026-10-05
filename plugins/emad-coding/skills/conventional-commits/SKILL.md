---
name: conventional-commits
description: >-
  Writes and checks git commit messages and pull request titles so they follow
  Conventional Commits (a type, an optional scope, and a short imperative
  description). Use when writing a commit message, naming or opening a pull
  request, squash-merging, or checking whether a message or title is correct.
license: MIT
---

# Conventional Commits

Every commit message and every pull request title follows
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Format

```text
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Rules

1. **Type** is one of these:
   - `feat`: a new capability for the user.
   - `fix`: a bug fix.
   - `docs`: documentation only.
   - `refactor`: a code change that neither fixes a bug nor adds a feature.
   - `test`: tests only.
   - `perf`: makes something faster or use fewer resources.
   - `build`: the build system or dependencies.
   - `ci`: continuous integration configuration.
   - `chore`: maintenance that fits nothing above.
   - `style`: formatting only, no change in behaviour.
   - `revert`: undoes an earlier commit.
2. **Scope** is optional. It names the area that changed, in lowercase: `feat(auth): ...`.
3. **Description** uses the imperative mood. It starts with a lowercase letter and has no
   trailing period. Aim for 50 characters, at most 72. Write `add token refresh`, not
   `Added token refresh.`
4. **Breaking change**: mark it with `!` after the type or scope (`feat(api)!: ...`), with a
   footer `BREAKING CHANGE: <what breaks and how to migrate>`, or with both. Either marker
   alone is valid. When you write a message, use both: `!` makes the break visible in the
   subject, and the footer says how to migrate.
5. **Body** is optional. It explains *why* the change is needed; the diff already shows
   *what* changed. Leave one blank line after the subject and wrap at 72 characters.
6. **Footers** come after one blank line: `Refs: #123`, `BREAKING CHANGE: ...`, and any
   trailer the project requires, such as `Co-Authored-By:`.

## Pull request titles

A pull request title follows the same format as a commit subject. When a pull request is
squash-merged, its title becomes the commit on the main branch, and release tools read that
commit to choose the next version. A title such as `Update auth` silently breaks releases.

## Choosing the type

- Judge what the change does for a user of the project, not which files it touches.
- If one change mixes several types, prefer to split it. If it cannot be split, choose the
  type with the biggest effect on users: `feat`, then `fix`, then the rest.
- A dependency update is `build(deps): ...`. A dependency update that fixes a security
  problem for users is `fix(deps): ...`.

## Steps

1. Read the diff, or the description of the change.
2. Pick the type. Add a scope when one area clearly owns the change.
3. Write the description: an imperative verb first, lowercase, no period.
4. Decide whether anything breaks for users. If it does, add `!` and a `BREAKING CHANGE:`
   footer. (When you check someone else's message, either marker alone is enough.)
5. Add a body only when the reason is not clear from the subject.
6. Output only the commit message or title, as plain text without a code block, unless the
   user asks for an explanation.

## Examples

| Wrong | Right |
| --- | --- |
| `Update auth` | `fix(auth): reject expired tokens on refresh` |
| `Added login endpoint.` | `feat(api): add login endpoint` |
| `M0+M1 engine` | `feat(engine): add query planner and executor` |
| `Remove v1 API` | `feat(api)!: remove v1 endpoints`, with the footer `BREAKING CHANGE: clients must call /v2` |

## Checking an existing message

When asked whether a message or title is correct, say whether it follows the rules. If it
does not, name each broken rule and give a corrected version. A breaking change marked only
with `!`, or only with a `BREAKING CHANGE:` footer, follows the rules.

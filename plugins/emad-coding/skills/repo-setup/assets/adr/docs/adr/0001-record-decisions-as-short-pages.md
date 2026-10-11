---
last_reviewed: __TODAY__
---

# 0001. Record decisions as short pages

**Status:** Accepted
**Date:** __TODAY__

## Context

People who join later cannot see why the code or the set-up looks the way it does. Chat history
and pull request threads are hard to search and are easy to lose.

## Decision

We write one short page for each decision that is hard to undo, or that a newcomer would
question. The pages live in `docs/adr/`, follow `template.md`, and are numbered. ADR means
Architecture Decision Record.

## Alternatives considered

- **Comments in code.** They describe one place, go stale, and hide the larger picture.
- **A wiki.** It sits apart from the code, so nobody reviews it together with the change.
- **Nothing.** The reasons then live in people's memories.

## Consequences

- A new decision costs about ten minutes of writing, at the time the alternatives are fresh.
- The history stays honest, because an accepted record is never edited. A changed decision is a
  new record.
- Reviewers can ask "is there a record for this?" instead of asking the author to explain again.

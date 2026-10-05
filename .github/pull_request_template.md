## What and why

<!-- What changes, and what problem it solves. The diff shows what; explain why. -->

## Checklist

- [ ] The title follows [Conventional Commits](https://www.conventionalcommits.org/). It
      becomes the commit on `main`. A skill behaviour change is `feat` or `fix`, not `docs`.
- [ ] `just check` passes.
- [ ] Documentation is updated in this pull request (`docs/`, and `README.md` for a new
      plugin).
- [ ] For a skill change: eval cases cover the new behaviour, and `just eval <plugin>/<skill>`
      passed locally (or the `run-evals` label was added after reading the diff).

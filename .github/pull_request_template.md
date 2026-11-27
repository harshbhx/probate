## What and why

<!-- One or two sentences. Link the issue: Closes #123 -->

## Checklist

- [ ] `make test` and `make lint` pass
- [ ] One coherent change per commit, in the `area: change` form
- [ ] No keys, tokens, `.env` files or real third-party addresses in the diff (`config/owner.yaml` stays untracked)
- [ ] Court changes fail closed, and `make site-data` was run if layer 1 output changed
- [ ] UI changes follow `docs/04-DESIGN.md` and were checked at 1280 px and 390 px
- [ ] Added a line to CHANGELOG.md under Unreleased
- [ ] Docs updated where behaviour changed

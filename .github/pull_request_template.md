## What

<!-- Brief summary of the change -->

## Why

<!-- What problem does this solve or what requirement does it address? -->

## How

<!-- Technical approach — skip for trivial changes -->

## Testing

<!-- How was this tested? The tests run, and what you ran to check the change works (docs/process.md, "run it"): the app, endpoint, CLI or script you used, against what, and what it showed. If something couldn't be run, say why. -->

## Known gaps

<!-- Anything deferred in the change itself: a gate finding left for later, behaviour that couldn't be run or tested. Each one also gets a row in docs/tech-debt.md. A gate that couldn't run is noted here only. Delete this section if there are none. -->

## Checklist

- [ ] Code follows project conventions
- [ ] Tests added/updated
- [ ] What was built was run and works as described (docs/process.md, "run it"), or the gap is noted under Testing and Known gaps
- [ ] Documentation updated (if applicable), including `AGENTS.md` if project context changed
- [ ] Pre-PR gates from `docs/process.md` run and findings folded in, and which of them saw the final diff (antigravity runs on every PR; if the `agy` CLI was unavailable, say so in this description)
- [ ] No secrets or credentials committed
- [ ] Commit messages follow Conventional Commits

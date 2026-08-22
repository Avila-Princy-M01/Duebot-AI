## What

<!-- One sentence: what does this PR do? -->

## Why

<!-- Why is this change needed? Link to context if applicable. -->

## How

<!-- Brief description of the approach. Call out any notable decisions. -->

## Safety Checklist

- [ ] No safety invariants violated (read `skills.md` §6.2)
- [ ] Audit log updated for any state transitions
- [ ] No hardcoded secrets, URLs, or API keys
- [ ] New env vars documented in `.env.example`
- [ ] Type hints on all new functions
- [ ] Docstrings on all new public functions/classes

## Tests

- [ ] New tests added for new logic
- [ ] Existing tests still pass (`pytest tests/unit/ -v`)
- [ ] Coverage maintained or improved

## Checklist

- [ ] `ruff format .` passes
- [ ] `ruff check .` passes
- [ ] `mypy --strict backend/` passes
- [ ] `npm run build` passes (if frontend changes)
- [ ] `ARCHITECTURE.md` updated (if system design changed)
- [ ] Commit messages follow Conventional Commits

## Demo Impact

<!-- Does this change affect the demo? If yes, what should the judge see? -->

## Screenshots / recordings

<!-- If UI changes, attach before/after. -->

## 📝 Description

Please provide a clear and concise description of the changes in this pull request.

## ✔️ Checklist

- [ ] I have read the [**CONTRIBUTING.md**](CONTRIBUTING.md) document.
- [ ] My code follows the style guidelines of this project (Black 79, flake8, mypy clean).
- [ ] I have added tests to cover my changes (repository minimum: 90% coverage, never lowered).
- [ ] I have added an example in the `examples/` directory (if applicable).
- [ ] I have updated the documentation (if applicable) and every new Python block runs in CI.
- [ ] I have commented on my code, especially in hard-to-understand areas — architecture comments explain *why*.
- [ ] All new and existing tests passed.
- [ ] I have updated `CHANGELOG.md` **and** `docs/_guide/changelog.md` (they must stay identical).

### 🔌 If this touches `xstate_statemachine.contrib`, `persistence`, or the engine hooks

- [ ] The core is still zero-dependency: `pytest tests/test_zero_dependency.py` passes.
- [ ] The extra imports cleanly **with** its dependency and raises `MissingExtraError` (naming the `pip install` command) **without** it: `pytest tests/contrib/test_extras_matrix.py`.
- [ ] `contrib/_registry.py`, `pyproject.toml` extras and the CI `contrib` matrix agree.
- [ ] The integration's docs page follows `docs/_templates/integration-page.md` and has both the **Guarantees** and **Threat model** boxes.
- [ ] The relevant items of the [security & operability baseline (#303)](https://github.com/basiltt/xstate-statemachine/issues/303) are cited in the tests.
- [ ] The issue's verification script (`scripts/verify/<issue>.py`) was run and its output is pasted below.
- [ ] Both engines (`Interpreter` and `SyncInterpreter`) are covered where the change touches shared semantics.
- [ ] **This PR does not tag or publish a release.** Releases happen only after the maintainer's explicit confirmation.

## 🔗 Related Issues

Closes # (if applicable)

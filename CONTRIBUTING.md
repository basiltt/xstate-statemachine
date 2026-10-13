# 🤝 Contributing to XState-StateMachine

First off, thank you for considering contributing! This project is open to all, and we welcome any contributions, from bug fixes to new features.

## 🚀 How to Contribute

We follow the standard "Fork & Pull Request" workflow.

1.  **Fork** the repository to your own GitHub account.
2.  **Clone** your fork to your local machine:
    `git clone https://github.com/basiltt/xstate-statemachine.git`
3.  **Create a feature branch** from the `main` branch:
    `git checkout -b <branch-type>/<short-description>`
    (e.g., `feat/add-new-feature`, `fix/correct-a-bug`)
4.  **Set up the development environment**:
    `uv pip install -e . --group dev --group lint --group test`
5.  **Install pre-commit hooks** to ensure code style consistency:
    `uv run pre-commit install`

## ✨ Making Your Changes

-   Make your code changes.
-   Add or update tests in the `tests/` directory to cover your changes.
-  Add an example in the `examples/` directory if applicable.
-   Add a bullet under `## [Unreleased]` in **both** `CHANGELOG.md` and `docs/_guide/changelog.md` (the two must stay byte-identical; a test enforces it).
-   Commit your changes with a descriptive message following the [Conventional Commits](httpshttps://www.conventionalcommits.org/) specification (e.g., `feat: Add support for XYZ`).

## 🧪 Running Tests

Before submitting your pull request, please run the full test suite to ensure that your changes have not introduced any regressions.

Run the following command from the root of the project:

```bash
uv run pytest
```

This will automatically find and execute all tests in the tests/ directory. All tests must pass before a pull request can be merged.

Coverage is a repository rule: the suite must keep **at least 90%** line and branch coverage (`fail_under` in `pyproject.toml`). `uv run pytest --cov` reports it and fails below the bar, exactly as CI does. New code should arrive with tests that keep the number where it is or move it up; the threshold is only ever raised.

## 📬 Submitting Your Pull Request

1.  **Push** your feature branch to your fork on GitHub:
    `git push -u origin <branch-name>`
2.  **Open a Pull Request** to the `main` branch of the original repository.
3.  Fill out the pull request template with a clear description of your changes.
4.  Ensure all automated CI checks pass.

## 🏷️ Cutting a release (maintainers)

1. Move the `## [Unreleased]` entries in **both** `CHANGELOG.md` and `docs/_guide/changelog.md` under the new version heading (the two copies must stay identical).
   Use the actual release date and leave an empty Unreleased section for future changes.
2. Align `__version__` in `src/xstate_statemachine/__init__.py`, `pyproject.toml`, `docs/_config.yml`, and the documented action/hook pins. Regenerate `uv.lock` with `uv lock` (without `--upgrade`), then verify it with `uv lock --check`; this does not require syncing or changing the working environment.
3. Run the full tests and formatting checks, wait for the intended release revision's CI checks to pass, and merge the release changes to `main`. Verify the merged revision's CI and GitHub Pages deployment. The Publish workflow validates distributions but does **not** replace the full test, lint, and coverage gates.
4. Build and validate the distributions with `python -m build` and `twine check dist/*`, and smoke-test the installed wheel in a clean environment. Confirm that the target version is not already published on PyPI and that its tag does not already point elsewhere.
5. Tag and push **`v<version>`** on the verified main commit — `git tag v0.11.0 <verified-main-sha> && git push origin v0.11.0`. The `xsm-check` GitHub Action (`uses: basiltt/xstate-statemachine@v<version>`) and the pre-commit hooks (`rev: v<version>`) documented in the CLI guide resolve through this tag; `tests/test_battle_309_docs_truth.py` keeps the documented pins equal to `__version__`, so a release without its tag leaves every copy-paste snippet dead.
6. Publish one non-prerelease GitHub release from that existing tag. The `release: published` event starts `.github/workflows/publish.yml`, which rebuilds and publishes to PyPI through Trusted Publishing. Do **not** also dispatch a manual PyPI upload for the same version.
7. Watch Publish through success. Compare the uploaded wheel and source archive's SHA-256 hashes with PyPI's version metadata; use the Publish run's `dist` artifact if attaching those files to the GitHub release. Independently rebuilt artifacts need not have identical bytes.
8. Install the exact released version from PyPI in a clean environment outside the checkout, verify the runtime/metadata version and CLI, and check the live site's version, release notes, and representative desktop/mobile pages.

Thank you for your contribution!

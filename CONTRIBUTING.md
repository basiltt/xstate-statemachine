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
    `poetry install`
5.  **Install pre-commit hooks** to ensure code style consistency:
    `pre-commit install`

## ✨ Making Your Changes

-   Make your code changes.
-   Add or update tests in the `tests/` directory to cover your changes.
-  Add an example in the `examples/` directory if applicable.
-   Update the `docs/CHANGELOG.md` file under the "Next Release" section.
-   Commit your changes with a descriptive message following the [Conventional Commits](httpshttps://www.conventionalcommits.org/) specification (e.g., `feat: Add support for XYZ`).

## 🧪 Running Tests

Before submitting your pull request, please run the full test suite to ensure that your changes have not introduced any regressions.

Run the following command from the root of the project:

```bash
poetry run pytest
```

This will automatically find and execute all tests in the tests/ directory. All tests must pass before a pull request can be merged.

## 📬 Submitting Your Pull Request

1.  **Push** your feature branch to your fork on GitHub:
    `git push -u origin <branch-name>`
2.  **Open a Pull Request** to the `main` branch of the original repository.
3.  Fill out the pull request template with a clear description of your changes.
4.  Ensure all automated CI checks pass.

Thank you for your contribution!

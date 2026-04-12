# Contributing to Agon PromptRank

Thank you for your interest in contributing to Agon PromptRank! We aim to build an inclusive, collaborative community to scale gamified AI metrics across the enterprise industry.

## How to Contribute

### 1. Reporting Bugs
If you find a bug, please create an Issue using the GitHub tracker. Ensure you include:
- A clear, descriptive title.
- Steps to reproduce the issue.
- Details regarding your environment (OS, Python version).

### 2. Suggesting Features
We welcome features, especially those extending `AIToolPlugin` abstract methods to support tools like ChatGPT, Claude, Cursor, and Copilot. Submit an issue detailing your feature. Provide a brief breakdown of implementation ideas if applicable.

### 3. Submitting Pull Requests
- Fork the repository.
- Create a new feature branch (`git checkout -b feature/your-feature-name`).
- Commit your changes utilizing descriptive, imperative commit messages.
- Add/update tests where applicable.
- Push to your branch and open a Pull Request against the `main` branch.

## Code Standards
- **Python**: We strictly adhere to PEP-8 guidelines and PEP-484 type-hinting. Run `black` and `flake8` to format/lint before opening PRs.
- **Frontend**: Stick to the Tailwind utility-class design philosophy. Avoid writing custom CSS inside the repository unless extending the base config. Prefer standard HTMX partial polling where Reactivity is needed.

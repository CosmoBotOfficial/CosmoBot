# Contributing to CosmoBot

First off, thank you for considering contributing to CosmoBot! Your time and efforts are greatly appreciated. This guide will help you get started with contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
   - [Reporting Bugs](#reporting-bugs)
   - [Suggesting Features](#suggesting-features)
   - [Contributing Code](#contributing-code)
3. [Getting Started](#getting-started)
   - [Setting Up the Development Environment](#setting-up-the-development-environment)
   - [Making Your Changes](#making-your-changes)
4. [Style Guidelines](#style-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [License](#license)

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful and considerate to others in all interactions.

## How Can I Contribute?

### Reporting Bugs

If you find a bug, please open an issue on GitHub. Include as much detail as possible:

- A clear and descriptive title.
- Steps to reproduce the issue.
- Any relevant log output or screenshots.
- The version of CosmoBot and your environment setup (e.g., Python version, Discord.py version).

### Suggesting Features

We welcome feature requests! If you have an idea for improving CosmoBot, please open an issue on GitHub and:

- Explain the problem your feature would solve.
- Describe the proposed solution.
- Mention any alternatives you've considered.

### Contributing Code

We welcome contributions from everyone, whether you're fixing a bug or adding a new feature. Please ensure that your code follows our [Style Guidelines](#style-guidelines).

## Getting Started

### Setting Up the Development Environment

1. **Fork the repository** to your GitHub account.
2. **Clone your fork** to your local machine:

   ```bash
   git clone https://github.com/YOUR-USERNAME/CosmoBot.git
   
## Install the dependencies:

```bash
pdm install requirements.txt
```

## Set up environment variables:

Create a `.env` file in the root of the project and add your Discord bot token and other necessary configurations.

```makefile
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

## Run the bot locally to ensure everything is set up correctly:

```bash
python bot.py
```

## Making Your Changes

### Create a new branch for your feature or bugfix:

```bash
git checkout -b feature/your-feature-name
```

### Make your changes, and ensure the bot runs correctly.

### Commit your changes with a descriptive message:

```bash
git commit -m "Add feature: Your feature description"
```

### Push your changes to your forked repository:

```bash
git push origin feature/your-feature-name
```

### Open a Pull Request on the original repository.

## Style Guidelines

- **Code Style**: Follow [PEP 8](https://pep8.org/) for Python code.
- **Docstrings**: Use [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
- **Commit Messages**: Write clear and concise commit messages. Use the present tense ("Add feature" not "Added feature").

## Pull Request Process

1. Ensure your branch is up-to-date with the `main` branch.
2. Submit a detailed Pull Request on GitHub, describing your changes.
3. A project maintainer will review your PR. Please be patient and responsive to feedback.
4. Once approved, your PR will be merged into the `main` branch.

## License

By contributing to CosmoBot, you agree that your contributions will be licensed under the AGPL-3.0 License.

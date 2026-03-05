# Contributing to lobstr-cli

Thanks for your interest in contributing!

## Getting started

1. Fork the repo and clone it locally
2. Install in development mode:

```bash
pip install -e ".[dev]"
```

3. Run tests to make sure everything works:

```bash
pytest
```

## Making changes

1. Create a branch for your change:

```bash
git checkout -b my-feature
```

2. Make your changes and add tests
3. Run the test suite:

```bash
pytest -v
```

4. Lint your code:

```bash
ruff check src/ tests/
```

5. Commit and push your branch, then open a pull request

## Code style

- Follow existing patterns in the codebase
- Use type hints
- Keep functions focused and small
- Add tests for new functionality

## Project structure

```
src/lobstr_cli/
    __init__.py          # Package version
    __main__.py          # Entry point
    cli.py               # Root Typer app, global flags
    client.py            # HTTP client with error handling
    config.py            # TOML config management
    display.py           # Rich output helpers
    resolve.py           # Hash/name resolution utilities
    commands/
        auth.py          # config and whoami commands
        crawlers.py      # crawler browsing
        squid.py         # squid management
        task.py          # task management
        run.py           # run lifecycle
        go.py            # one-shot workflow
        results.py       # result fetching
tests/
    test_client.py       # HTTP client tests
    test_config.py       # Config tests
    test_resolve.py      # Resolution logic tests
    test_display.py      # Display output tests
    test_cli.py          # CLI integration tests
    test_commands_*.py   # Command-level tests
```

## Reporting issues

Open an issue at [github.com/lobstrio/lobstr-cli/issues](https://github.com/lobstrio/lobstr-cli/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- CLI version (`lobstr --version`)

## Pull requests

- Keep PRs focused on a single change
- Include tests
- Update CHANGELOG.md if adding features or fixing bugs
- Reference related issues in the PR description

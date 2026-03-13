# Contributing to lobstrio-cli

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
    config.py            # TOML config management
    display.py           # Rich output helpers
    resolve.py           # Hash/name resolution utilities
    commands/
        accounts.py      # account management and sync
        auth.py          # config and whoami commands
        crawlers.py      # crawler browsing
        delivery.py      # delivery configuration
        squid.py         # squid management
        task.py          # task management
        run.py           # run lifecycle
        go.py            # one-shot workflow
        results.py       # result fetching
tests/
    test_client.py       # SDK error types and client tests
    test_config.py       # Config tests
    test_resolve.py      # Resolution logic tests
    test_display.py      # Display output tests
    test_cli.py          # CLI integration tests
    test_commands_*.py   # Command-level tests
```

## Reporting issues

Open an issue at [github.com/lobstrio/lobstrio-cli/issues](https://github.com/lobstrio/lobstrio-cli/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- CLI version (`lobstr --version`)

## Versioning

We follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

| Bump | When | Examples |
|------|------|----------|
| **PATCH** (`0.1.0` → `0.1.1`) | Bug fixes, typo corrections, small tweaks — no new features, nothing breaking | Fix crash on empty results, fix typo in help text |
| **MINOR** (`0.1.0` → `0.2.0`) | New features, new commands, new options — backwards compatible | Add `crawlers show` command, add slug resolution |
| **MAJOR** (`0.2.0` → `1.0.0`) | Breaking changes — renamed/removed commands, changed output format, changed config format | Rename `squid` to `scraper`, change JSON output schema |

While the major version is `0` (pre-1.0), the API is not considered stable and minor bumps may include small breaking changes.

When bumping the version:
1. Update `version` in `pyproject.toml`
2. Add a new section at the top of `CHANGELOG.md` with the date and changes

## Pull requests

- Keep PRs focused on a single change
- Include tests
- Update CHANGELOG.md if adding features or fixing bugs
- Reference related issues in the PR description

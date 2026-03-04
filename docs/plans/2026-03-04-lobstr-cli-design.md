# lobstr CLI Design

## Overview

CLI tool wrapping the Lobstr.io scraping API. Covers Phases 1-5: foundation, crawlers, squid/task CRUD, run lifecycle, and the `go` power command.

## Tech Stack

- **CLI framework:** typer
- **HTTP client:** httpx (sync)
- **Config:** TOML at `~/.config/lobstr/config.toml`
- **Output:** rich (tables, progress bars, colors)
- **Distribution:** `pip install lobstr-cli`, entry point `lobstr`

## Architecture

```
src/lobstr_cli/
  __init__.py
  __main__.py          # python -m lobstr_cli
  cli.py               # Root typer app + global options (--json, --token, --verbose, --quiet)
  client.py            # LobstrClient: sync httpx wrapper, auth, error handling, rate limits
  config.py            # TOML config read/write (~/.config/lobstr/config.toml)
  display.py           # Rich tables, progress bars, detail views, JSON output mode
  resolve.py           # Hash prefix resolution, crawler name fuzzy matching
  commands/
    __init__.py
    auth.py            # config set-token, config show, whoami
    crawlers.py        # crawlers ls/params/search
    squid.py           # squid create/ls/show/update/empty/rm
    task.py            # task add/upload/upload-status/ls/show/rm
    run.py             # run start/ls/show/stats/tasks/abort/download/watch
    go.py              # go (full workflow power command)
```

## Key Decisions

- **Sync httpx** — simpler than async, sufficient for sequential polling
- **Typer** — auto-help, type validation, clean group nesting
- **Positional squid args** — `lobstr task add <squid> <url>` not `--squid`
- **Hash prefix matching** — resolve unique prefixes against full hash lists
- **Crawler name matching** — case-insensitive substring for `squid create`

## API Path Corrections (vs plan.md)

| Plan | Actual |
|------|--------|
| GET /balance | GET /v1/user/balance |
| POST /accounts/{id}/sync | POST /v1/accounts/cookies |
| GET /accounts/{id}/sync-status | GET /v1/synchronize/{id} |
| POST /accounts/{id}/limits | POST /v1/accounts (with account field) |
| GET /runs/{id}/tasks | GET /v1/runtasks?run= |
| POST /delivery/test | POST /v1/delivery/test-{route} |

## Error Handling

- Client raises: AuthError, NotFoundError, RateLimitError, APIError
- Commands catch and display Rich-formatted errors
- --verbose shows full request/response
- --json outputs raw JSON on success, JSON error on failure

## The `go` Command

1. Resolve crawler (name or hash prefix)
2. Create temporary squid
3. Add tasks (URLs from args or --file)
4. Set params/accounts/concurrency if provided
5. Start run
6. Poll with Rich progress bar
7. Download CSV to --output path
8. Print summary
9. On Ctrl+C: print squid/run IDs for manual resume

## Config File

```toml
[auth]
token = "..."

[defaults]
output_format = "csv"
concurrency = 1
download_dir = "."

[aliases]
reviews = "4b1ba006..."
```

Aliases accessed via `@name` prefix in any squid/hash argument.

# `lobstr` CLI — Design Plan

## Philosophy

The Lobstr API is async: create squid → add tasks → configure → run → poll → download. The CLI should make the common path trivial (one command) while exposing every endpoint for power users. Think `gh` (GitHub CLI) or `fly` (Fly.io) — short verbs, smart defaults, hash prefixes instead of full hashes.

---

## API Summary (base: `https://api.lobstr.io/v1`)

| Resource    | Endpoints |
|-------------|-----------|
| Auth        | `GET /me`, `GET /balance` |
| Crawlers    | `GET /crawlers`, `GET /crawlers/{hash}/params` |
| Squids      | `POST /squids`, `POST /squids/{hash}` (update), `GET /squids`, `GET /squids/{hash}`, `POST /squids/{hash}/empty`, `DELETE /squids/{hash}` |
| Tasks       | `POST /tasks`, `POST /tasks/upload`, `GET /tasks?squid=`, `GET /tasks/{id}`, `DELETE /tasks/{id}`, `GET /tasks/upload/{id}` (check upload) |
| Runs        | `POST /runs`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/stats`, `GET /runs/{id}/tasks`, `POST /runs/{id}/abort`, `GET /runs/{id}/download` |
| Results     | `GET /results?squid=` |
| Accounts    | `GET /accounts`, `GET /account-types`, `GET /accounts/{id}`, `POST /accounts/{id}/sync`, `GET /accounts/{id}/sync-status`, `POST /accounts/{id}/limits`, `POST /accounts/{id}/refresh-cookies`, `DELETE /accounts/{id}` |
| Delivery    | `POST /delivery?squid=` (email/sftp/gsheet/s3/webhook), `POST /delivery/test?squid=` |

---

## Command Tree

```
lobstr
│
├── config                          # First-time setup
│   ├── set-token                   # Store API key in ~/.config/lobstr/config.toml
│   └── show                        # Print current config (masked token)
│
├── whoami                          # GET /me + GET /balance (quick health check)
│
├── crawlers                        # Discovery
│   ├── ls                          # GET /crawlers (table: name | hash | description)
│   ├── params <crawler>            # GET /crawlers/{hash}/params
│   └── search <keyword>            # Client-side filter on crawler list
│
├── squid                           # Squid management
│   ├── create <crawler>            # POST /squids  — accepts hash OR name substring
│   ├── ls                          # GET /squids (table: name | hash | crawler | tasks)
│   ├── show <squid>                # GET /squids/{hash}
│   ├── update <squid> [OPTIONS]    # POST /squids/{hash}
│   │       --concurrency N
│   │       --accounts ID [ID...]
│   │       --param KEY=VALUE       # repeatable, sets params.KEY
│   │       --notify on_success|on_error|never
│   │       --unique-results / --no-unique-results
│   ├── empty <squid>               # POST /squids/{hash}/empty
│   └── rm <squid>                  # DELETE /squids/{hash}
│
├── task                            # Task (input URL) management
│   ├── add <squid> <url> [url...]  # POST /tasks — squid is positional, not a flag
│   ├── upload <squid> <file>       # POST /tasks/upload (csv/txt/tsv)
│   ├── upload-status <upload_id>   # GET /tasks/upload/{id}
│   ├── ls <squid>                  # GET /tasks?squid=
│   │       --limit N --offset N
│   ├── show <task_id>              # GET /tasks/{id}
│   └── rm <task_id>                # DELETE /tasks/{id}
│
├── run                             # Run lifecycle
│   ├── start <squid>               # POST /runs
│   │       --wait                  # Poll until done, then print summary
│   │       --download [path]       # Implies --wait, download CSV on completion
│   ├── ls [--squid HASH]           # GET /runs
│   │       --status running|done|error
│   │       --limit N
│   ├── show <run_id>               # GET /runs/{id}
│   ├── stats <run_id>              # GET /runs/{id}/stats (live progress)
│   ├── tasks <run_id>              # GET /runs/{id}/tasks
│   ├── abort <run_id>              # POST /runs/{id}/abort
│   ├── download <run_id> [path]    # GET /runs/{id}/download → save CSV
│   └── watch <run_id>              # Live-poll stats with progress bar
│
├── results                         # Result fetching
│   └── get <squid>                 # GET /results?squid=
│           --format csv|json       # Default: csv
│           --output <path>
│
├── account                         # Social account management
│   ├── ls                          # GET /accounts
│   ├── types                       # GET /account-types
│   ├── show <id>                   # GET /accounts/{id}
│   ├── sync <id>                   # POST /accounts/{id}/sync
│   ├── sync-status <id>            # GET /accounts/{id}/sync-status
│   ├── update-limits <id>          # POST /accounts/{id}/limits
│   ├── refresh-cookies <id>        # POST /accounts/{id}/refresh-cookies
│   └── rm <id>                     # DELETE /accounts/{id}
│
├── delivery                        # Export configuration
│   ├── set <squid> --email | --sftp | --gsheet | --s3 | --webhook [OPTIONS]
│   └── test <squid>                # POST /delivery/test
│
└── go <crawler> [OPTIONS]          # ⚡ THE POWER COMMAND (full workflow)
        <url> [url...]              # URLs to scrape
        --file <path>               # Or a file of URLs
        --param KEY=VALUE           # Crawler params
        --accounts ID [ID...]
        --concurrency N
        --output <path>             # Where to save results (default: ./results.csv)
        --no-download               # Just start, don't wait
```

---

## Key Design Decisions

### 1. `go` — One Command to Rule Them All

Most users just want: "scrape these URLs with this crawler and give me a CSV." The `go` command does the entire workflow:

```bash
# Scrape Google Maps reviews for 3 places, save to reviews.csv
lobstr go "Google Maps Reviews" \
  "https://maps.google.com/?cid=123" \
  "https://maps.google.com/?cid=456" \
  --param max_pages=5 \
  --output reviews.csv
```

Under the hood: create squid → add tasks → start run → poll → download → cleanup (optional).

### 2. Squid as Positional Arg, Not Flag

Your original `--squid {hash}` pattern forces users to remember a flag name for something that's always required. Positional is cleaner:

```bash
# Yours
lobstr task add --url https://example.com --squid abc123

# Proposed — squid is the context, URLs are the payload
lobstr task add abc123 https://example.com https://other.com
```

### 3. Hash Prefix Matching

Nobody wants to type `5c11752d8687df2332c08247c4fb655a`. The CLI should resolve unique prefixes:

```bash
lobstr squid show 5c117    # resolves to full hash
lobstr run stats 1d66f     # same
```

### 4. Crawler Name Matching

`lobstr squid create` should accept a name (fuzzy) not just a hash:

```bash
lobstr squid create "linkedin profile"   # fuzzy matches → LinkedIn Profile Scraper
lobstr squid create 5c11752d             # also works with hash/prefix
```

### 5. `run start --wait --download` Combo Flags

Since the API is async, the most common follow-up after starting is poll+download. Bake it in:

```bash
lobstr run start abc123 --download ./output.csv
# Starts run → shows progress bar → downloads when done
```

### 6. `run watch` — Live Progress

A dedicated subcommand that live-polls `runs/{id}/stats` and renders a progress bar:

```
$ lobstr run watch 1d66f
⣾ Running... 67% [████████████░░░░░░] 134/200 tasks  2m12s elapsed
```

---

## Tech Stack

| Layer              | Choice                  | Why |
|--------------------|-------------------------|-----|
| CLI framework      | `typer`                 | Group nesting, auto-help, type validation |
| HTTP client        | `httpx`                 | Async support for Wpolling, cleaner than requests |
| Config storage     | `~/.config/lobstr/`     | XDG-compliant, TOML format |
| Output formatting  | `rich`                  | Tables, progress bars, colored output |
| Distribution       | `pip install lobstr-cli` | Single `pyproject.toml`, entry point `lobstr` |

---

## Project Structure

```
lobstr-cli/
├── pyproject.toml
├── README.md
├── src/
│   └── lobstr_cli/
│       ├── __init__.py
│       ├── __main__.py          # python -m lobstr_cli
│       ├── cli.py               # Root click group + global options
│       ├── client.py            # LobstrClient — thin wrapper around httpx
│       ├── config.py            # Token storage, config loading
│       ├── display.py           # Rich tables, progress bars, formatters
│       ├── resolve.py           # Hash prefix resolution, crawler name matching
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── auth.py          # config, whoami
│       │   ├── crawlers.py      # crawlers ls/params/search
│       │   ├── squid.py         # squid create/ls/show/update/empty/rm
│       │   ├── task.py          # task add/upload/ls/show/rm
│       │   ├── run.py           # run start/ls/show/stats/tasks/abort/download/watch
│       │   ├── results.py       # results get
│       │   ├── account.py       # account ls/types/show/sync/rm
│       │   ├── delivery.py      # delivery set/test
│       │   └── go.py            # go (full workflow)
│       └── models.py            # Pydantic models for API responses (optional)
└── tests/
    ├── test_client.py
    ├── test_resolve.py
    └── conftest.py
```

---

## Implementation Order

| Phase | What | Commands | Effort |
|-------|------|----------|--------|
| **1** | Foundation | `config set-token`, `whoami`, `client.py`, `config.py` | 1 day |
| **2** | Discovery | `crawlers ls`, `crawlers params`, `crawlers search` | 0.5 day |
| **3** | Core CRUD | `squid create/ls/show/update/rm`, `task add/upload/ls/rm` | 1.5 days |
| **4** | Run lifecycle | `run start/ls/show/stats/abort/download/watch` | 1.5 days |
| **5** | Power command | `go` (end-to-end workflow) | 1 day |
| **6** | Extras | `account *`, `delivery *`, `results get` | 1 day |
| **7** | Polish | Hash prefix resolution, fuzzy matching, error handling, `--json` global flag | 1 day |

**Total: ~7-8 days for a solid v1.**

---

## Global Flags (on every command)

```
--json          Output raw JSON instead of formatted tables
--token TOKEN   Override stored token (useful for scripts/CI)
--verbose       Show request/response details for debugging
--quiet         Suppress non-essential output
```

---

## Config File (`~/.config/lobstr/config.toml`)

```toml
[auth]
token = "9425a66eba999..."

[defaults]
output_format = "csv"       # csv | json
concurrency = 1
download_dir = "."

[aliases]                   # Custom squid aliases
reviews = "4b1ba00657cd4e4798f49309c82fbb06"
linkedin = "a1b2c3d4e5f6"
```

Aliases let users do:
```bash
lobstr run start @reviews        # @ prefix = alias lookup
lobstr task add @linkedin https://linkedin.com/in/someone
```

---

## Example Workflows

### Quick one-liner
```bash
lobstr go "vinted products" "https://www.vinted.fr/catalog?search=nike" -o vinted.csv
```

### Reusable squid setup
```bash
lobstr squid create "linkedin profile" --name "my-li-scraper"
lobstr squid update my-li --concurrency 3 --accounts acc1 acc2 --param email=true
lobstr task upload my-li urls.txt
lobstr run start my-li --download profiles.csv
```

### Scriptable pipeline
```bash
SQUID=$(lobstr squid create google-maps-reviews --json | jq -r .id)
lobstr task add $SQUID $URLS
RUN=$(lobstr run start $SQUID --json | jq -r .id)
lobstr run watch $RUN
lobstr run download $RUN ./data/reviews-$(date +%F).csv
```
<p align="center">
  <img src="https://raw.githubusercontent.com/lobstrio/lobstrio-cli/main/.github/logo.svg" alt="Lobstr.io" width="80"><br>
  <strong>lobstrio</strong><br>
  <em>Command-line interface for the <a href="https://lobstr.io">Lobstr.io</a> scraping API</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/lobstrio/"><img src="https://img.shields.io/pypi/v/lobstrio?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/lobstrio/"><img src="https://img.shields.io/pypi/pyversions/lobstrio" alt="Python"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/actions"><img src="https://img.shields.io/github/actions/workflow/status/lobstrio/lobstrio-cli/test.yml?label=tests" alt="Tests"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lobstrio/lobstrio-cli" alt="License"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/issues"><img src="https://img.shields.io/github/issues/lobstrio/lobstrio-cli" alt="Issues"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/pulls"><img src="https://img.shields.io/github/issues-pr/lobstrio/lobstrio-cli" alt="PRs"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/stargazers"><img src="https://img.shields.io/github/stars/lobstrio/lobstrio-cli" alt="Stars"></a>
  <a href="https://github.com/lobstrio/lobstrio-cli/network/members"><img src="https://img.shields.io/github/forks/lobstrio/lobstrio-cli" alt="Forks"></a>
  <a href="https://pypi.org/project/lobstrio/"><img src="https://img.shields.io/pypi/dm/lobstrio" alt="Downloads"></a>
  <img src="https://img.shields.io/badge/code%20style-ruff-d4aa00" alt="Ruff">
</p>

---

Run web scrapers, manage squids, download results — all from your terminal.

## Demo

<!-- Replace with a terminal GIF recording (e.g. using asciinema or vhs) for maximum impact -->

```
$ lobstr go google-maps-leads-scraper "https://maps.google.com/maps/search/pizza+paris" -o results.csv

  Crawler   Google Maps Leads Scraper
  Squid     google-maps-leads-scraper-a8f2 (created)
  Tasks     1 added
  Run       started (e4b2c9d1...)

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 00:42 ETA 0:00

  ✓ Downloaded 247 results → results.csv
```

## Installation

```bash
pip install lobstrio
```

Requires Python 3.10+.

## Quick start

```bash
# Save your API token (find it at https://app.lobstr.io/dashboard/api)
lobstr config set-token YOUR_TOKEN

# One-command scrape: create squid, add tasks, run, download
lobstr go google-maps-leads-scraper "https://maps.google.com/maps/place/..." -o leads.csv

# Multiple URLs
lobstr go google-maps-leads-scraper url1 url2 url3 -o results.csv

# From a file
lobstr go google-maps-leads-scraper --file urls.txt -o results.csv
```

## Commands

<details>
<summary><strong>Account &amp; config</strong></summary>

```bash
lobstr whoami                          # Show account info and balance
lobstr config set-token TOKEN          # Save API token
lobstr config show                     # Show current config
lobstr config set-alias maps SQUID     # Create alias for a squid
```

</details>

<details>
<summary><strong>Crawlers</strong> — browse the scraper catalog</summary>

```bash
lobstr crawlers ls                                   # List all available crawlers
lobstr crawlers show google-maps-leads-scraper       # Show crawler details
lobstr crawlers search "Google Maps"                 # Search by name
lobstr crawlers params google-maps-leads-scraper     # Show crawler parameters
lobstr crawlers attrs google-maps-leads-scraper      # Show result attributes
```

</details>

<details>
<summary><strong>Squids</strong> — manage scraper instances</summary>

```bash
lobstr squid create google-maps-leads-scraper --name "My Scraper"
lobstr squid ls                        # List your squids
lobstr squid show SQUID                # Show details
lobstr squid update SQUID --concurrency 5 --param max_results=200
lobstr squid empty SQUID               # Remove all tasks
lobstr squid rm SQUID --force          # Delete squid
```

</details>

<details>
<summary><strong>Tasks</strong> — manage input URLs and keywords</summary>

```bash
lobstr task add SQUID url1 url2        # Add tasks
lobstr task add SQUID "pizza" --key keyword  # Keyword-based crawlers
lobstr task ls SQUID                   # List tasks
lobstr task show FULL_TASK_HASH        # Show task details
lobstr task rm FULL_TASK_HASH          # Delete task
lobstr task upload SQUID tasks.csv     # Bulk upload from CSV
lobstr task upload-status UPLOAD_ID    # Check upload progress
```

</details>

<details>
<summary><strong>Runs</strong> — start, monitor, and download</summary>

```bash
lobstr run start SQUID                 # Start a run
lobstr run start SQUID --wait          # Start and wait for completion
lobstr run start SQUID --download results.csv  # Start, wait, download
lobstr run ls SQUID                    # List runs
lobstr run show FULL_RUN_HASH          # Show run details
lobstr run stats FULL_RUN_HASH         # Show run statistics
lobstr run tasks FULL_RUN_HASH         # List tasks in a run
lobstr run watch FULL_RUN_HASH         # Live progress bar
lobstr run abort FULL_RUN_HASH         # Stop a run
lobstr run download FULL_RUN_HASH      # Download results CSV
```

</details>

<details>
<summary><strong>Results</strong> — fetch scraped data</summary>

```bash
lobstr results get SQUID               # Fetch results (JSON)
lobstr results get SQUID --format csv  # Fetch as CSV
lobstr results get SQUID -o data.json  # Save to file
```

</details>

<details>
<summary><strong>Accounts</strong> — manage connected platform accounts</summary>

```bash
lobstr accounts ls                     # List all accounts
lobstr accounts show ACCOUNT           # Show account details
lobstr accounts types                  # List available account types
lobstr accounts sync --type google --cookies-file cookies.json  # Sync account
lobstr accounts sync-status SYNC_ID    # Check sync progress
lobstr accounts update ACCOUNT --param daily_limit=100
lobstr accounts rm ACCOUNT --force     # Delete account
```

</details>

<details>
<summary><strong>Delivery</strong> — configure result delivery</summary>

```bash
lobstr delivery email SQUID --email you@example.com
lobstr delivery googlesheet SQUID --url "https://docs.google.com/..."
lobstr delivery s3 SQUID --bucket my-bucket --target-path scrapes/
lobstr delivery webhook SQUID --url "https://your-server.com/hook"
lobstr delivery sftp SQUID --host ftp.example.com --username user --password pass

# Test connectivity
lobstr delivery test-email --email you@example.com
lobstr delivery test-s3 --bucket my-bucket
```

</details>

<details open>
<summary><strong>Go</strong> — full workflow in one command</summary>

```bash
# Basic usage
lobstr go google-maps-leads-scraper "https://maps.google.com/..." -o results.csv

# Keyword-based crawler
lobstr go google-search-scraper "pizza delivery" --key keyword

# With crawler parameters
lobstr go google-maps-leads-scraper url1 --param max_results=200 --param language=English

# Set concurrency
lobstr go google-maps-leads-scraper url1 --concurrency 3

# Start without waiting for download
lobstr go google-maps-leads-scraper url1 --no-download

# Reuse existing squid by name
lobstr go google-maps-leads-scraper url1 --name "My Leads"

# Clear old tasks when reusing squid
lobstr go google-maps-leads-scraper url1 --name "My Leads" --empty

# Delete squid after completion
lobstr go google-maps-leads-scraper url1 --delete

# Custom output file
lobstr go google-maps-leads-scraper url1 -o my_leads.csv
```

</details>

## Global flags

| Flag | Description |
|------|-------------|
| `--json` | Output raw JSON (for piping/scripting) |
| `--quiet` | Suppress non-essential output |
| `--verbose` | Show HTTP request details |
| `--token TOKEN` | Override API token for this command |
| `--version` | Show version |

## Aliases

Create shortcuts for frequently used squids:

```bash
lobstr config set-alias maps abc123def456...
lobstr task ls @maps
lobstr run start @maps
```

## Identifier resolution

| Resource | Resolution order | Example |
|----------|-----------------|---------|
| **Crawlers** | Hash prefix → Slug (exact/prefix) → Name (exact/substring) | `google-maps`, `4734d096`, `"Google Maps"` |
| **Squids** | `@alias` → Hash prefix → Name (exact/substring) | `@maps`, `abc1`, `"My Scraper"` |
| **Accounts** | Hash prefix → Username (exact/substring) | `f9a2`, `"john@gmail.com"` |
| **Runs & Tasks** | Full 32-character hash only | `a1b2c3d4e5f6...` |

## Configuration

Config is stored at `~/.config/lobstr/config.toml`. The API token can also be set via the `LOBSTR_TOKEN` environment variable.

## CLI vs SDK

| | **CLI** (`pip install lobstrio`) | **SDK** (`pip install lobstrio-sdk`) |
|---|---|---|
| **Use case** | Terminal workflows, quick scrapes, cron jobs | Scripts, pipelines, applications |
| **Interface** | Shell commands | Python API |
| **Output** | Rich tables, progress bars, CSV files | Typed dataclass models |
| **Async** | No | Yes (`AsyncLobstrClient`) |
| **Pagination** | Manual (`--page`, `--limit`) | Auto (`client.squids.iter()`) |

For programmatic access, see [lobstrio-sdk](https://github.com/lobstrio/lobstrio-sdk).

## FAQ

<details>
<summary><strong>Where do I get an API token?</strong></summary>

Go to [Dashboard → API](https://app.lobstr.io/dashboard/api) to find your token. It's always available there, pre-generated.

</details>

<details>
<summary><strong>How do I use keyword-based crawlers?</strong></summary>

Some crawlers accept keywords instead of URLs. Use the `--key` flag:

```bash
lobstr go google-search-scraper "pizza delivery" --key keyword
```

Use `lobstr crawlers params <crawler>` to see what parameters a crawler accepts.

</details>

<details>
<summary><strong>Can I use short hashes for runs and tasks?</strong></summary>

No. Run and task endpoints require the full 32-character hash. Use `lobstr run ls SQUID` or `lobstr task ls SQUID` to see full hashes. Crawlers and squids support prefix matching.

</details>

<details>
<summary><strong>How do I pipe results to other tools?</strong></summary>

Use `--json` for machine-readable output:

```bash
lobstr --json results get SQUID | jq '.[].email'
lobstr --json crawlers ls | jq '.[] | .name'
```

</details>

<details>
<summary><strong>Can I run scrapes in the background?</strong></summary>

Yes. Use `--no-download` with `go`, or start a run without `--wait`:

```bash
lobstr go google-maps-leads-scraper urls.txt --no-download
lobstr run start SQUID  # returns immediately
lobstr run watch RUN_HASH  # check progress later
```

</details>

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and versioning guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[Apache 2.0](LICENSE)

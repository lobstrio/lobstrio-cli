# lobstrio-cli

Command-line interface for the [Lobstr.io](https://lobstr.io) scraping API.

Run web scrapers, manage squids, download results — all from your terminal.

## Installation

```bash
pip install lobstrio-cli
```

## Quick start

```bash
# Save your API token (get it at https://app.lobstr.io/dashboard/api)
lobstr config set-token YOUR_TOKEN

# One-command scrape: create squid, add tasks, run, download
lobstr go "Google Maps Leads" "https://maps.google.com/maps/place/..." -o leads.csv

# Multiple URLs
lobstr go "Google Maps Leads" url1 url2 url3 -o results.csv

# From a file
lobstr go "Google Maps Leads" --file urls.txt -o results.csv
```

## Commands

### Account

```bash
lobstr whoami                          # Show account info and balance
lobstr config set-token TOKEN          # Save API token
lobstr config show                     # Show current config
lobstr config set-alias maps SQUID_ID  # Create alias for a squid
```

### Crawlers

```bash
lobstr crawlers ls                     # List all available crawlers
lobstr crawlers search "Google Maps"   # Search by name
lobstr crawlers params "Google Maps"   # Show crawler parameters
```

### Squids

```bash
lobstr squid create "Google Maps" --name "My Scraper"
lobstr squid ls                        # List your squids
lobstr squid show SQUID_HASH           # Show details
lobstr squid update SQUID --concurrency 5 --param max_results=200
lobstr squid empty SQUID               # Remove all tasks
lobstr squid rm SQUID --force          # Delete squid
```

### Tasks

```bash
lobstr task add SQUID url1 url2        # Add tasks
lobstr task add SQUID "pizza" --key keyword  # Keyword-based crawlers
lobstr task ls SQUID                   # List tasks
lobstr task show FULL_TASK_HASH        # Show task details
lobstr task rm FULL_TASK_HASH          # Delete task
lobstr task upload SQUID tasks.csv     # Bulk upload from CSV
lobstr task upload-status UPLOAD_ID    # Check upload progress
```

### Runs

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

### Results

```bash
lobstr results get SQUID               # Fetch results (JSON)
lobstr results get SQUID --format csv  # Fetch as CSV
lobstr results get SQUID -o data.json  # Save to file
```

### Go (full workflow)

The `go` command handles the entire workflow in one shot:

```bash
# Basic usage
lobstr go "Google Maps Leads" "https://maps.google.com/..." -o results.csv

# Keyword-based crawler
lobstr go "Google Search" "pizza delivery" --key keyword

# With crawler parameters
lobstr go "Google Maps" url1 --param max_results=200 --param language=English

# Set concurrency
lobstr go "Google Maps" url1 --concurrency 3

# Start without waiting for download
lobstr go "Google Maps" url1 --no-download

# Reuse existing squid by name
lobstr go "Google Maps" url1 --name "My Leads"

# Clear old tasks when reusing squid
lobstr go "Google Maps" url1 --name "My Leads" --empty

# Delete squid after completion
lobstr go "Google Maps" url1 --delete

# Custom output file
lobstr go "Google Maps" url1 -o my_leads.csv
```

## Global flags

```bash
lobstr --json ...      # Output raw JSON (for piping/scripting)
lobstr --quiet ...     # Suppress non-essential output
lobstr --verbose ...   # Show HTTP request details
lobstr --token T ...   # Override API token for this command
lobstr --version       # Show version
```

## Aliases

Create shortcuts for frequently used squids:

```bash
lobstr config set-alias maps abc123def456...
lobstr task ls @maps
lobstr run start @maps
```

## Configuration

Config is stored at `~/.config/lobstr/config.toml`. The API token can also be set via the `LOBSTR_TOKEN` environment variable.

## Hash prefixes

Squid and crawler hashes support prefix matching — type just enough characters to be unique:

```bash
lobstr squid show abc1    # Matches abc123def456...
```

Run and task commands require full 32-character hashes. Use `lobstr run ls` or `lobstr task ls` to see full hashes.

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/lobstrio/lobstr-cli.git
cd lobstr-cli
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

## License

[MIT](LICENSE)

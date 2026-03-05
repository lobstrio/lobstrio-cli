# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-03-05

### Added

- Full CLI for the Lobstr.io scraping API
- `go` command for one-shot scraping workflow (create squid, add tasks, run, download)
- Crawler browsing and search (`crawlers ls`, `crawlers search`, `crawlers params`)
- Squid management (`squid create`, `ls`, `show`, `update`, `empty`, `rm`)
- Task management (`task add`, `ls`, `show`, `rm`, `upload`, `upload-status`)
- Run lifecycle (`run start`, `ls`, `show`, `stats`, `tasks`, `abort`, `download`, `watch`)
- Results export in JSON and CSV formats
- Config management with TOML storage (`config set-token`, `show`, `set-alias`)
- `whoami` command for account info and balance
- Hash prefix resolution for squids and crawlers
- Squid aliases (`@name` shortcuts)
- Global flags: `--json`, `--quiet`, `--verbose`, `--token`
- `--key` flag for keyword-based crawlers
- `--delete` flag to clean up squid after `go` completes
- `--empty` flag to clear old tasks when reusing a squid
- Squid reuse by `--name` in `go` command
- Auto-cleanup of orphaned squids on error
- Download retry with export wait
- Full hash validation for run/task endpoints
- Rich terminal output with tables and progress bars

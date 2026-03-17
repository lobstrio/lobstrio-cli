# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-17

### Added

- `crawlers attrs` command — show result attributes grouped by function with colored output
- `--limit` and `--page` pagination for `accounts ls`
- `--limit` alias for `--page-size` in `results get`
- Animated terminal demo GIF in README
- GitHub Actions CI (test + publish workflows)
- FAQ, CLI vs SDK comparison, and extra badges in README

### Changed

- `crawlers search` now shows same columns as `crawlers ls` (slug, max concurrency, etc.)

## [0.4.0] - 2026-03-13

### Changed

- Replaced internal HTTP client with `lobstrio-sdk` for all API calls
- All commands now use typed SDK models and resource methods
- Removed `pytest-httpx` dev dependency (tests mock SDK methods directly)

### Removed

- Deleted internal `client.py` (replaced by `lobstrio-sdk`)

### Fixed

- Fixed double CLI execution when invoked via console script entry point
- Fixed install command in README (`pip install lobstrio`, not `lobstrio-cli`)

## [0.3.0] - 2026-03-06

### Added

- Account management commands: `accounts ls`, `show`, `rm`, `types`, `sync`, `sync-status`, `update`
- Account sync with multiple cookie input methods: `--cookie`, `--cookies-json`, `--cookies-file`
- Account resolution by hash prefix or username
- Delivery configuration commands: `delivery email`, `googlesheet`, `s3`, `webhook`, `sftp`
- Delivery test commands: `delivery test-email`, `test-googlesheet`, `test-s3`, `test-webhook`, `test-sftp`
- `crawlers show` now uses dedicated API endpoint with input parameters and result fields
- Query params support in `client.post()` for delivery endpoints

## [0.2.0] - 2026-03-06

### Added

- Slug-based resolution for crawlers: hash → slug → name (slug is now the primary identifier)
- Slug prefix matching for crawlers (e.g. `google-maps` matches `google-maps-leads-scraper`)
- Name-based resolution for squids: alias → hash → name (exact match, then substring)
- `crawlers show` command with grouped detail output (credits, flags, worker stats)
- `print_detail_grouped` display function for sectioned detail views
- Slug column in `crawlers ls` output

### Changed

- License changed from MIT to Apache 2.0
- Crawler commands now prioritize slug over name for identification
- README updated with slug-based examples and identifier resolution documentation

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

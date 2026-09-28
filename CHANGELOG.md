# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.2] - 2026-09-28

### Added

- `--function NAME` turns an add-on on (`NAME=false` turns it off), repeatable,
  in `go` and `squid update`: `lobstr go youtube-channel-scraper <url> --function get_videos`.
  Names are checked against the crawler's add-ons. Before, only the SDK could set them.

### Fixed

- `squid update --param/--function`, and `go` reusing a squid by `--name`, keep the
  squid's saved params. The API replaces `params` as a whole, so sending only the
  change dropped the rest (e.g. `[400] A required parameter language is missing`).

## [0.7.1] - 2026-09-16

### Fixed

- `go` no longer hardcodes the task key `url`. It now defaults `--key` from
  the crawler's own declared task params: the one param when it declares
  exactly one (e.g. `department` for `1stdibs-iter-categories`, instead of
  the `[400] Invalid param: url` it used to return after already creating
  and deleting a squid for nothing), `url` when it declares several and
  `url` is one of them, and `url` when it declares none. When it declares
  several and none of them is `url`, `go` refuses to guess and names the
  choices instead — pass one with `--key`. An explicit `--key` always wins
  over the default.

## [0.7.0] - 2026-09-15

### Added

- Link a connected platform account to a squid with `squid update --account`
  and `go --account`, without detaching accounts already attached. Linking
  is additive by default: pass an account and it's added to whatever the
  squid already has. `squid update --replace-accounts` replaces the whole
  list instead — including detaching every account when used with no
  `--account` at all — and prints which accounts are being detached before
  it does. Requires `lobstrio-sdk>=0.7.0`.
- `go` picks the right account automatically for an account-backed crawler
  (e.g. LinkedIn, Sales Navigator) when exactly one healthy, unlocked match
  exists for that crawler's account type, and tells you what to pass when it
  cannot: it names the candidates when there are several, or what type of
  account to connect when there are none. It never auto-picks onto a squid
  that already has an account attached — a reused squid (`go --name`) keeps
  whatever it had.
  This closes a gap where `go` on an account-backed crawler would create the
  squid and start the run, and the run would fail immediately with no
  account ever linked, even with a healthy matching account already
  connected (visible in `lobstr accounts ls`).
- `go` creates the squid and links the account in one command; a wrong-type
  account, an unknown account, or `--account` on a crawler that doesn't use
  one each fail with a message telling you what to do, before anything is
  created. If linking fails after the squid is created — or the command is
  interrupted (Ctrl-C) — before the run starts, the squid is deleted instead
  of left behind.

### Changed

- `crawlers ls`, `show`, and `search` now show which account type a crawler
  needs (e.g. `sales-nav-sync`) in the "Needs Account" column, instead of a
  plain yes/no — use it to find a matching account for `--account`. `--json`
  output is unaffected; it already returned the full crawler details.

## [0.6.1] - 2026-09-11

### Fixed

- `go` on a crawler whose squid-level params are all optional (e.g.
  `linkedin-profile-email-scraper-no-login`) failed with `SquidNotReady` when
  no `--param`/`--concurrency` was passed. A squid is created with
  `is_ready=false`, and `POST /squids/{hash}` only flips it when the update
  actually persists a field — an empty body, or `{"params": {}}`, is a
  no-op on the API side, so `go`'s previous fix (always sending the update
  call, even empty) did not actually fix anything. `go` now fetches the
  crawler's squid-level params and sends them all (the user's `--param`
  value, or `null` for the ones left unset) so the update body is never
  empty; a crawler with no squid-level params at all (e.g.
  `httpbin-get-json`) instead re-sends the squid's own name, which the API
  always persists. A squid param marked required is never sent as `null`:
  if the user didn't pass it with `--param`, `go` now fails before creating
  the squid, naming the missing param(s), instead of creating an orphaned
  squid and failing later with `ParamsNeeded` or `SquidNotReady`.

## [0.6.0] - 2026-09-10

### Fixed

- `crawlers ls`, `crawlers search`, `crawlers show`, `crawlers params`,
  `crawlers attrs`, `squid create`, and `go` only ever saw the **first page**
  of the crawler catalog — 50 of ~183 crawlers. Any crawler past page 1 (e.g.
  the LinkedIn Profile & Email Scraper (No Login), on page 4) could not be
  listed, searched, shown, or instantiated from the CLI. These commands now
  walk every page.

  The catalog was never restricted to crawlers assigned to the account: the
  full store was always reachable, just page-capped. The API offers no
  server-side search and caps `limit` at 120, so paging is the only fix.

- `crawlers show/params/attrs <full-32-char-hash>` failed with
  `No match for prefix` even for a valid hash, because the hash was validated
  against that same first page. A complete hash now goes straight to the API,
  which also makes it a single request instead of a full catalog walk. An
  unknown hash surfaces the API's own 404.

- Resolving a squid by name/prefix or an account by username also read only the
  first page, so anything past the 50th was invisible. Both now paginate.

### Changed

- `crawlers search` matches the slug as well as the name, so
  `crawlers search no-login` works and not just `crawlers search "no login"`.

- Require `lobstrio-sdk>=0.6.0` (adds `accounts.iter()`).

## [0.5.2] - 2026-09-09

### Added

- `squid estimate <id>` — authoritative pre-run cost/result estimate from the API
  (per-service credits, total credits, estimated time, projected max results,
  task count). The squid must have at least one task.
- `squid update` gains `--active/--inactive`, `--to-complete`, the
  `--no-line-breaks/--line-breaks` export toggle, `--cron`, and `--timezone`.

### Changed

- Require `lobstrio-sdk>=0.5.0` (adds `squids.estimate()` and the new
  `squids.update()` fields).

## [0.5.1] - 2026-09-08

### Added

- Send `User-Agent: lobstrio-cli/<version>` on every request. The API attributes
  requests from this header — e.g. it records a squid's creation source (`cli`)
  from it, so squids created via the CLI are now distinguishable from raw API and
  SDK usage.

### Changed

- Require `lobstrio-sdk>=0.3.0` (the version that accepts `user_agent=`).

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

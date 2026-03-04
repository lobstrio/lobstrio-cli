# lobstr CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool (`lobstr`) that wraps the Lobstr.io scraping API, covering config, crawlers, squid/task CRUD, run lifecycle, and a `go` power command.

**Architecture:** Typer-based CLI with nested sub-apps per resource. Sync httpx client handles all API calls. Rich library for tables/progress. Config stored in TOML at `~/.config/lobstr/config.toml`.

**Tech Stack:** Python 3.10+, typer, httpx, rich, tomli/tomli-w, pyproject.toml (hatchling)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/lobstr_cli/__init__.py`
- Create: `src/lobstr_cli/__main__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lobstr-cli"
version = "0.1.0"
description = "CLI for the Lobstr.io scraping API"
requires-python = ">=3.10"
dependencies = [
    "typer[all]>=0.9.0",
    "httpx>=0.27.0",
    "rich>=13.0.0",
    "tomli>=2.0.0;python_version<'3.11'",
    "tomli-w>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.30.0",
    "ruff>=0.4.0",
]

[project.scripts]
lobstr = "lobstr_cli.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/lobstr_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create package files**

`src/lobstr_cli/__init__.py`:
```python
"""lobstr CLI — command-line interface for the Lobstr.io scraping API."""

__version__ = "0.1.0"
```

`src/lobstr_cli/__main__.py`:
```python
from lobstr_cli.cli import app

app()
```

`tests/conftest.py`:
```python
import pytest
```

**Step 3: Install in dev mode and verify**

Run: `cd /home/matrix/mdev/lobstrio-cli && pip install -e ".[dev]"`
Expected: Installs successfully

Run: `python -c "import lobstr_cli; print(lobstr_cli.__version__)"`
Expected: `0.1.0`

**Step 4: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffolding with pyproject.toml"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/lobstr_cli/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing tests**

`tests/test_config.py`:
```python
import pytest
from pathlib import Path


def test_get_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import get_config_dir
    assert get_config_dir() == tmp_path / "lobstr"


def test_save_and_load_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, load_config
    save_token("test-token-123")
    cfg = load_config()
    assert cfg["auth"]["token"] == "test-token-123"


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import load_config
    cfg = load_config()
    assert cfg == {}


def test_get_token_from_env(monkeypatch):
    monkeypatch.setenv("LOBSTR_TOKEN", "env-token-456")
    from lobstr_cli.config import get_token
    assert get_token() == "env-token-456"


def test_get_token_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LOBSTR_TOKEN", raising=False)
    from lobstr_cli.config import save_token, get_token
    save_token("config-token-789")
    assert get_token() == "config-token-789"


def test_save_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, save_alias, load_config
    save_token("tok")
    save_alias("reviews", "abc123hash")
    cfg = load_config()
    assert cfg["aliases"]["reviews"] == "abc123hash"


def test_resolve_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, save_alias, resolve_alias
    save_token("tok")
    save_alias("reviews", "abc123hash")
    assert resolve_alias("@reviews") == "abc123hash"
    assert resolve_alias("not-an-alias") == "not-an-alias"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

`src/lobstr_cli/config.py`:
```python
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
import tomli_w


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    return base / "lobstr"


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _save_config(cfg: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(cfg, f)


def save_token(token: str) -> None:
    cfg = load_config()
    cfg.setdefault("auth", {})["token"] = token
    _save_config(cfg)


def get_token(override: str | None = None) -> str | None:
    if override:
        return override
    env = os.environ.get("LOBSTR_TOKEN")
    if env:
        return env
    cfg = load_config()
    return cfg.get("auth", {}).get("token")


def save_alias(name: str, hash_value: str) -> None:
    cfg = load_config()
    cfg.setdefault("aliases", {})[name] = hash_value
    _save_config(cfg)


def resolve_alias(value: str) -> str:
    if not value.startswith("@"):
        return value
    name = value[1:]
    cfg = load_config()
    aliases = cfg.get("aliases", {})
    if name in aliases:
        return aliases[name]
    return value
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/lobstr_cli/config.py tests/test_config.py
git commit -m "feat: config module with token storage, aliases, XDG support"
```

---

### Task 3: HTTP Client

**Files:**
- Create: `src/lobstr_cli/client.py`
- Create: `tests/test_client.py`

**Step 1: Write the failing tests**

`tests/test_client.py`:
```python
import pytest
import httpx
from pytest_httpx import HTTPXMock
from lobstr_cli.client import LobstrClient, AuthError, NotFoundError, APIError


@pytest.fixture
def client():
    return LobstrClient(token="test-token")


def test_client_auth_header(client: LobstrClient):
    assert client._client.headers["authorization"] == "Token test-token"


def test_client_base_url(client: LobstrClient):
    assert str(client._client.base_url) == "https://api.lobstr.io/v1/"


def test_get_me(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/me",
        json={"id": "u1", "email": "test@example.com", "name": "Test"},
    )
    result = client.get("/me")
    assert result["email"] == "test@example.com"


def test_post_json(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids",
        json={"id": "sq1", "name": "Test Squid"},
    )
    result = client.post("/squids", json={"crawler": "abc123"})
    assert result["id"] == "sq1"


def test_auth_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/me",
        status_code=401,
        json={"error": "Invalid token"},
    )
    with pytest.raises(AuthError):
        client.get("/me")


def test_not_found_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids/nonexist",
        status_code=404,
        json={"error": "Not found"},
    )
    with pytest.raises(NotFoundError):
        client.get("/squids/nonexist")


def test_api_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/runs",
        status_code=400,
        json={"error": "Squid has no tasks"},
    )
    with pytest.raises(APIError, match="Squid has no tasks"):
        client.post("/runs", json={"squid": "abc"})


def test_delete(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids/abc123",
        json={"id": "abc123", "deleted": True},
    )
    result = client.delete("/squids/abc123")
    assert result["deleted"] is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_client.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

`src/lobstr_cli/client.py`:
```python
from __future__ import annotations

import httpx


class APIError(Exception):
    def __init__(self, status_code: int, message: str, body: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.body = body or {}
        super().__init__(f"[{status_code}] {message}")


class AuthError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    pass


BASE_URL = "https://api.lobstr.io/v1/"


class LobstrClient:
    def __init__(self, token: str, verbose: bool = False):
        self.verbose = verbose
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"authorization": f"Token {token}"},
            timeout=30.0,
        )

    def _handle_response(self, resp: httpx.Response) -> dict:
        if self.verbose:
            import sys
            print(f"  {resp.request.method} {resp.request.url} -> {resp.status_code}", file=sys.stderr)

        body = {}
        try:
            body = resp.json()
        except Exception:
            pass

        if resp.status_code == 401:
            raise AuthError(401, body.get("error", "Authentication failed"), body)
        if resp.status_code == 404:
            raise NotFoundError(404, body.get("error", "Not found"), body)
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after", "?")
            raise RateLimitError(429, f"Rate limited. Retry after {retry_after}s", body)
        if resp.status_code >= 400:
            raise APIError(resp.status_code, body.get("error", resp.text), body)

        return body

    def get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(path, params=params)
        return self._handle_response(resp)

    def post(self, path: str, json: dict | None = None, data: dict | None = None, files: dict | None = None) -> dict:
        resp = self._client.post(path, json=json, data=data, files=files)
        return self._handle_response(resp)

    def delete(self, path: str) -> dict:
        resp = self._client.delete(path)
        return self._handle_response(resp)

    def download(self, url: str, dest: str) -> None:
        """Download a file from a full URL (e.g., S3 signed URL) to dest path."""
        with httpx.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    def close(self) -> None:
        self._client.close()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_client.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/lobstr_cli/client.py tests/test_client.py
git commit -m "feat: HTTP client with error handling and typed exceptions"
```

---

### Task 4: Display Module

**Files:**
- Create: `src/lobstr_cli/display.py`

**Step 1: Write display.py**

```python
from __future__ import annotations

import json as json_mod
import sys
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import print as rprint

console = Console()
err_console = Console(stderr=True)

# Global state set by CLI callback
_json_mode = False
_quiet_mode = False


def set_output_mode(json_mode: bool = False, quiet: bool = False) -> None:
    global _json_mode, _quiet_mode
    _json_mode = json_mode
    _quiet_mode = quiet


def print_json(data: Any) -> None:
    console.print_json(json_mod.dumps(data, default=str))


def print_error(message: str) -> None:
    if _json_mode:
        print_json({"error": message})
    else:
        err_console.print(f"[bold red]Error:[/] {message}")


def print_success(message: str) -> None:
    if _quiet_mode:
        return
    if _json_mode:
        return
    err_console.print(f"[bold green]{message}[/]")


def print_info(message: str) -> None:
    if _quiet_mode:
        return
    if _json_mode:
        return
    err_console.print(f"[dim]{message}[/]")


def print_table(columns: list[str], rows: list[list[str]], title: str | None = None) -> None:
    table = Table(title=title, show_lines=False)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def print_detail(fields: list[tuple[str, Any]]) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    for name, value in fields:
        table.add_row(name, str(value) if value is not None else "[dim]—[/]")
    console.print(table)


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=err_console,
    )
```

**Step 2: Commit**

```bash
git add src/lobstr_cli/display.py
git commit -m "feat: display module with Rich tables, progress bars, output modes"
```

---

### Task 5: Resolve Module (Hash Prefix + Fuzzy Name Matching)

**Files:**
- Create: `src/lobstr_cli/resolve.py`
- Create: `tests/test_resolve.py`

**Step 1: Write the failing tests**

`tests/test_resolve.py`:
```python
import pytest
from lobstr_cli.resolve import match_hash_prefix, match_crawler_name


def test_match_hash_prefix_exact():
    items = [{"id": "abc123"}, {"id": "abc456"}, {"id": "def789"}]
    assert match_hash_prefix("abc123", items) == "abc123"


def test_match_hash_prefix_unique():
    items = [{"id": "abc123"}, {"id": "def456"}]
    assert match_hash_prefix("abc", items) == "abc123"


def test_match_hash_prefix_ambiguous():
    items = [{"id": "abc123"}, {"id": "abc456"}]
    with pytest.raises(SystemExit):
        match_hash_prefix("abc", items)


def test_match_hash_prefix_no_match():
    items = [{"id": "abc123"}]
    with pytest.raises(SystemExit):
        match_hash_prefix("xyz", items)


def test_match_crawler_name_exact():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "Google Maps Reviews"},
    ]
    assert match_crawler_name("LinkedIn Profile Scraper", crawlers) == "c1"


def test_match_crawler_name_substring():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "Google Maps Reviews"},
    ]
    assert match_crawler_name("linkedin profile", crawlers) == "c1"


def test_match_crawler_name_ambiguous():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "LinkedIn Company Scraper"},
    ]
    with pytest.raises(SystemExit):
        match_crawler_name("linkedin", crawlers)


def test_match_crawler_name_no_match():
    crawlers = [{"id": "c1", "name": "LinkedIn Profile Scraper"}]
    with pytest.raises(SystemExit):
        match_crawler_name("facebook", crawlers)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_resolve.py -v`
Expected: FAIL

**Step 3: Write implementation**

`src/lobstr_cli/resolve.py`:
```python
from __future__ import annotations

import sys
from lobstr_cli.display import print_error


def match_hash_prefix(prefix: str, items: list[dict], key: str = "id") -> str:
    matches = [item[key] for item in items if item[key].startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        print_error(f"No match for prefix '{prefix}'")
        raise SystemExit(1)
    # Check for exact match first
    if prefix in matches:
        return prefix
    print_error(f"Ambiguous prefix '{prefix}' matches: {', '.join(matches[:5])}")
    raise SystemExit(1)


def match_crawler_name(name: str, crawlers: list[dict]) -> str:
    lower = name.lower()
    # Exact match first
    for c in crawlers:
        if c["name"].lower() == lower:
            return c["id"]
    # Substring match
    matches = [c for c in crawlers if lower in c["name"].lower()]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) == 0:
        print_error(f"No crawler matching '{name}'")
        raise SystemExit(1)
    names = [m["name"] for m in matches[:5]]
    print_error(f"Ambiguous name '{name}' matches: {', '.join(names)}")
    raise SystemExit(1)


def resolve_crawler(identifier: str, crawlers: list[dict]) -> str:
    """Resolve a crawler identifier that could be a hash, prefix, or name."""
    # If it looks like a hex hash/prefix, try hash matching first
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), crawlers)
        except SystemExit:
            pass
    # Fall back to name matching
    return match_crawler_name(identifier, crawlers)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_resolve.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/lobstr_cli/resolve.py tests/test_resolve.py
git commit -m "feat: hash prefix resolution and crawler name fuzzy matching"
```

---

### Task 6: Root CLI + Auth Commands

**Files:**
- Create: `src/lobstr_cli/cli.py`
- Create: `src/lobstr_cli/commands/__init__.py`
- Create: `src/lobstr_cli/commands/auth.py`

**Step 1: Write cli.py**

`src/lobstr_cli/cli.py`:
```python
from __future__ import annotations

from typing import Optional
import typer

from lobstr_cli import __version__
from lobstr_cli.config import get_token
from lobstr_cli.client import LobstrClient
from lobstr_cli.display import set_output_mode, print_error

app = typer.Typer(
    name="lobstr",
    help="CLI for the Lobstr.io scraping API",
    no_args_is_help=True,
)

# Shared state
_state: dict = {}


def get_client() -> LobstrClient:
    """Get or create the HTTP client from global state."""
    if "client" not in _state:
        token = get_token(override=_state.get("token"))
        if not token:
            print_error("No API token. Run: lobstr config set-token <TOKEN>")
            raise typer.Exit(1)
        _state["client"] = LobstrClient(token=token, verbose=_state.get("verbose", False))
    return _state["client"]


@app.callback()
def main(
    json: bool = typer.Option(False, "--json", help="Output raw JSON"),
    token: Optional[str] = typer.Option(None, "--token", envvar="LOBSTR_TOKEN", help="Override API token"),
    verbose: bool = typer.Option(False, "--verbose", help="Show request/response details"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-essential output"),
    version: bool = typer.Option(False, "--version", help="Show version"),
):
    if version:
        typer.echo(f"lobstr {__version__}")
        raise typer.Exit()
    _state["json"] = json
    _state["token"] = token
    _state["verbose"] = verbose
    _state["quiet"] = quiet
    set_output_mode(json_mode=json, quiet=quiet)


# Register command groups
from lobstr_cli.commands.auth import config_app, whoami_app
app.add_typer(config_app, name="config", help="Configuration management")
app.registered_commands.extend(whoami_app.registered_commands)
```

**Step 2: Write auth commands**

`src/lobstr_cli/commands/__init__.py`:
```python
```

`src/lobstr_cli/commands/auth.py`:
```python
from __future__ import annotations

import typer

from lobstr_cli.config import save_token, load_config, get_config_path
from lobstr_cli.display import print_success, print_detail, print_json, print_error, print_table

config_app = typer.Typer(no_args_is_help=True)
whoami_app = typer.Typer()


@config_app.command("set-token")
def set_token(token: str = typer.Argument(..., help="Your Lobstr API token")):
    """Store your API token."""
    save_token(token)
    print_success(f"Token saved to {get_config_path()}")


@config_app.command("show")
def show_config():
    """Show current configuration."""
    from lobstr_cli.cli import _state
    cfg = load_config()
    if _state.get("json"):
        # Mask token in JSON output too
        masked = dict(cfg)
        if "auth" in masked and "token" in masked["auth"]:
            t = masked["auth"]["token"]
            masked["auth"]["token"] = t[:8] + "..." if len(t) > 8 else "***"
        print_json(masked)
        return
    token = cfg.get("auth", {}).get("token", "")
    masked = token[:8] + "..." if len(token) > 8 else "(not set)"
    fields = [
        ("Config file", str(get_config_path())),
        ("Token", masked),
    ]
    defaults = cfg.get("defaults", {})
    for k, v in defaults.items():
        fields.append((f"Default {k}", v))
    aliases = cfg.get("aliases", {})
    if aliases:
        for name, h in aliases.items():
            fields.append((f"Alias @{name}", h))
    print_detail(fields)


@whoami_app.command("whoami")
def whoami():
    """Show current user and balance."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    me = client.get("/me")
    balance = client.get("/user/balance")
    if _state.get("json"):
        print_json({**me, "balance": balance})
        return
    print_detail([
        ("Name", me.get("name")),
        ("Email", me.get("email")),
        ("Plan", me.get("subscription_plan")),
        ("Status", me.get("subscription_status")),
        ("Max Concurrency", me.get("max_concurrency")),
        ("Max Squids", me.get("max_squids")),
        ("Balance", f"{balance.get('balance', 0)} credits"),
        ("Pending Cost", balance.get("pending_cost", 0)),
    ])
```

**Step 3: Test manually**

Run: `lobstr --help`
Expected: Shows help with config, whoami commands

Run: `lobstr --version`
Expected: `lobstr 0.1.0`

Run: `lobstr config set-token test123`
Expected: Token saved message

Run: `lobstr config show`
Expected: Shows config with masked token

**Step 4: Commit**

```bash
git add src/lobstr_cli/cli.py src/lobstr_cli/commands/
git commit -m "feat: root CLI with config and whoami commands"
```

---

### Task 7: Crawlers Commands

**Files:**
- Create: `src/lobstr_cli/commands/crawlers.py`
- Modify: `src/lobstr_cli/cli.py` (register crawler app)

**Step 1: Write crawlers commands**

`src/lobstr_cli/commands/crawlers.py`:
```python
from __future__ import annotations

from typing import Optional
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_info

crawlers_app = typer.Typer(no_args_is_help=True)


@crawlers_app.command("ls")
def list_crawlers():
    """List all available crawlers."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get("/crawlers")
    items = data.get("data", data) if isinstance(data, dict) else data
    if _state.get("json"):
        print_json(data)
        return
    rows = []
    for c in items:
        status = ""
        if c.get("has_issues"):
            status = "[yellow]issues[/]"
        elif not c.get("is_available"):
            status = "[red]unavailable[/]"
        elif c.get("is_premium"):
            status = "[cyan]premium[/]"
        rows.append([
            c.get("name", ""),
            c.get("id", "")[:12],
            f"{c.get('credits_per_row', '?')}",
            str(c.get("max_concurrency", "")),
            "yes" if c.get("account") else "no",
            status,
        ])
    print_table(["Name", "Hash", "Credits/Row", "Max Conc.", "Needs Account", "Status"], rows)


@crawlers_app.command("params")
def crawler_params(crawler: str = typer.Argument(..., help="Crawler hash or prefix")):
    """Show parameters for a crawler."""
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    # Resolve crawler
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    crawler_id = resolve_crawler(crawler, items)
    data = client.get(f"/crawlers/{crawler_id}/params")
    if _state.get("json"):
        print_json(data)
        return
    # Task-level params
    task_params = data.get("task", {})
    if task_params:
        print_info("Task-level parameters:")
        rows = []
        for name, spec in task_params.items():
            rows.append([
                name,
                spec.get("type", ""),
                "yes" if spec.get("required") else "no",
                str(spec.get("default", "")),
                spec.get("regex", ""),
            ])
        print_table(["Name", "Type", "Required", "Default", "Regex"], rows)
    # Squid-level params
    squid_params = data.get("squid", {})
    funcs = squid_params.pop("functions", {}) if isinstance(squid_params, dict) else {}
    if squid_params:
        print_info("\nSquid-level parameters:")
        rows = []
        for name, spec in squid_params.items():
            if name == "functions":
                continue
            allowed = ", ".join(spec["allowed"]) if isinstance(spec.get("allowed"), list) else ""
            rows.append([
                name,
                str(spec.get("default", "")),
                "yes" if spec.get("required") else "no",
                allowed[:50],
            ])
        print_table(["Name", "Default", "Required", "Allowed Values"], rows)
    if funcs:
        print_info("\nOptional functions (extra credits):")
        rows = []
        for name, spec in funcs.items():
            rows.append([name, str(spec.get("credits_per_function", "")), str(spec.get("default", ""))])
        print_table(["Function", "Credits", "Default"], rows)


@crawlers_app.command("search")
def search_crawlers(keyword: str = typer.Argument(..., help="Search keyword")):
    """Search crawlers by name."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get("/crawlers")
    items = data.get("data", data) if isinstance(data, dict) else data
    lower = keyword.lower()
    matches = [c for c in items if lower in c.get("name", "").lower()]
    if _state.get("json"):
        print_json(matches)
        return
    if not matches:
        print_info(f"No crawlers matching '{keyword}'")
        return
    rows = []
    for c in matches:
        rows.append([c.get("name", ""), c.get("id", "")[:12], str(c.get("credits_per_row", "?"))])
    print_table(["Name", "Hash", "Credits/Row"], rows)
```

**Step 2: Register in cli.py — add after existing imports at bottom of cli.py:**

```python
from lobstr_cli.commands.crawlers import crawlers_app
app.add_typer(crawlers_app, name="crawlers", help="Browse and search crawlers")
```

**Step 3: Test manually**

Run: `lobstr crawlers --help`
Expected: Shows ls, params, search subcommands

**Step 4: Commit**

```bash
git add src/lobstr_cli/commands/crawlers.py src/lobstr_cli/cli.py
git commit -m "feat: crawlers ls, params, and search commands"
```

---

### Task 8: Squid Commands

**Files:**
- Create: `src/lobstr_cli/commands/squid.py`
- Modify: `src/lobstr_cli/cli.py` (register squid app)

**Step 1: Write squid commands**

`src/lobstr_cli/commands/squid.py`:
```python
from __future__ import annotations

from typing import Optional
import typer

from lobstr_cli.config import resolve_alias
from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_error

squid_app = typer.Typer(no_args_is_help=True)


def _resolve_squid(client, identifier: str) -> str:
    identifier = resolve_alias(identifier)
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    from lobstr_cli.resolve import match_hash_prefix
    return match_hash_prefix(identifier, items)


@squid_app.command("create")
def create_squid(
    crawler: str = typer.Argument(..., help="Crawler hash, prefix, or name"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
):
    """Create a new squid for a crawler."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    # Resolve crawler
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    from lobstr_cli.resolve import resolve_crawler
    crawler_id = resolve_crawler(crawler, items)
    body: dict = {"crawler": crawler_id}
    if name:
        body["name"] = name
    result = client.post("/squids", json=body)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Created squid: {result.get('name')} ({result.get('id', '')[:12]})")


@squid_app.command("ls")
def list_squids(
    name: Optional[str] = typer.Option(None, "--name", help="Filter by name"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List your squids."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    params = {"limit": limit, "page": page}
    if name:
        params["name"] = name
    data = client.get("/squids", params=params)
    if _state.get("json"):
        print_json(data)
        return
    items = data.get("data", [])
    rows = []
    for s in items:
        rows.append([
            s.get("name", ""),
            s.get("id", "")[:12],
            s.get("crawler_name", ""),
            str(s.get("to_complete", "")),
            s.get("last_run_status", "") or "—",
            str(s.get("concurrency", 1)),
        ])
    print_table(["Name", "Hash", "Crawler", "Tasks", "Last Run", "Conc."], rows)


@squid_app.command("show")
def show_squid(squid: str = typer.Argument(..., help="Squid hash or prefix")):
    """Show squid details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    data = client.get(f"/squids/{squid_id}")
    if _state.get("json"):
        print_json(data)
        return
    print_detail([
        ("Name", data.get("name")),
        ("Hash", data.get("id")),
        ("Crawler", data.get("crawler_name")),
        ("Active", data.get("is_active")),
        ("Ready", data.get("is_ready")),
        ("Concurrency", data.get("concurrency")),
        ("Tasks", data.get("to_complete")),
        ("Last Run", data.get("last_run_status")),
        ("Last Run At", data.get("last_run_at")),
        ("Total Runs", data.get("total_runs")),
        ("Unique Results", data.get("export_unique_results")),
        ("Params", data.get("params")),
    ])


@squid_app.command("update")
def update_squid(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency"),
    name: Optional[str] = typer.Option(None, "--name"),
    notify: Optional[str] = typer.Option(None, "--notify", help="on_success|on_error|null"),
    unique_results: Optional[bool] = typer.Option(None, "--unique-results/--no-unique-results"),
    param: Optional[list[str]] = typer.Option(None, "--param", help="KEY=VALUE, repeatable"),
):
    """Update squid configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    body: dict = {}
    if concurrency is not None:
        body["concurrency"] = concurrency
    if name is not None:
        body["name"] = name
    if notify is not None:
        body["run_notify"] = None if notify == "null" else notify
    if unique_results is not None:
        body["export_unique_results"] = unique_results
    if param:
        params = {}
        for p in param:
            k, _, v = p.partition("=")
            params[k] = v
        body["params"] = params
    if not body:
        print_error("No options specified. Use --help to see available options.")
        raise typer.Exit(1)
    result = client.post(f"/squids/{squid_id}", json=body)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Updated squid {squid_id[:12]}")


@squid_app.command("empty")
def empty_squid(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    type: str = typer.Option("url", "--type", help="url or params"),
):
    """Remove all tasks from a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.post(f"/squids/{squid_id}/empty", json={"type": type})
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Emptied {result.get('deleted_count', '?')} tasks from {squid_id[:12]}")


@squid_app.command("rm")
def delete_squid(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a squid permanently."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    if not force:
        typer.confirm(f"Delete squid {squid_id[:12]}? This is permanent.", abort=True)
    result = client.delete(f"/squids/{squid_id}")
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted squid {squid_id[:12]}")
```

**Step 2: Register in cli.py:**

```python
from lobstr_cli.commands.squid import squid_app
app.add_typer(squid_app, name="squid", help="Squid management")
```

**Step 3: Commit**

```bash
git add src/lobstr_cli/commands/squid.py src/lobstr_cli/cli.py
git commit -m "feat: squid create, ls, show, update, empty, rm commands"
```

---

### Task 9: Task Commands

**Files:**
- Create: `src/lobstr_cli/commands/task.py`
- Modify: `src/lobstr_cli/cli.py` (register task app)

**Step 1: Write task commands**

`src/lobstr_cli/commands/task.py`:
```python
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.config import resolve_alias
from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_info, print_error

task_app = typer.Typer(no_args_is_help=True)


def _resolve_squid(client, identifier: str) -> str:
    identifier = resolve_alias(identifier)
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    from lobstr_cli.resolve import match_hash_prefix
    return match_hash_prefix(identifier, items)


@task_app.command("add")
def add_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    urls: list[str] = typer.Argument(..., help="URLs to add as tasks"),
):
    """Add URL tasks to a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    tasks = [{"url": url} for url in urls]
    result = client.post("/tasks", json={"squid": squid_id, "tasks": tasks})
    if _state.get("json"):
        print_json(result)
        return
    created = result.get("tasks", [])
    dupes = result.get("duplicated_count", 0)
    print_success(f"Added {len(created)} tasks ({dupes} duplicates skipped)")


@task_app.command("upload")
def upload_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    file: Path = typer.Argument(..., help="CSV/TSV file path", exists=True),
):
    """Upload tasks from a CSV/TSV file."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    with open(file, "rb") as f:
        result = client.post("/tasks/upload", data={"squid": squid_id}, files={"file": (file.name, f)})
    if _state.get("json"):
        print_json(result)
        return
    upload_id = result.get("id", "")
    print_success(f"Upload started: {upload_id}")
    print_info(f"Check status with: lobstr task upload-status {upload_id}")


@task_app.command("upload-status")
def upload_status(upload_id: str = typer.Argument(..., help="Upload task ID")):
    """Check upload progress."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.get(f"/tasks/upload/{upload_id}")
    if _state.get("json"):
        print_json(result)
        return
    meta = result.get("meta", {})
    print_detail([
        ("State", result.get("state")),
        ("Valid", meta.get("valid")),
        ("Inserted", meta.get("inserted")),
        ("Duplicates", meta.get("duplicates")),
        ("Invalid", meta.get("invalid")),
    ])


@task_app.command("ls")
def list_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List tasks for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    data = client.get("/tasks", params={"squid": squid_id, "limit": limit, "page": page})
    if _state.get("json"):
        print_json(data)
        return
    items = data.get("data", [])
    rows = []
    for t in items:
        params = t.get("params", {})
        url = params.get("url", str(params)[:60])
        rows.append([
            t.get("id", "")[:12],
            "yes" if t.get("is_active") else "no",
            str(url)[:70],
            t.get("created_at", "")[:10],
        ])
    print_table(["Hash", "Active", "URL/Params", "Created"], rows)


@task_app.command("show")
def show_task(task_id: str = typer.Argument(..., help="Task hash")):
    """Show task details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get(f"/tasks/{task_id}")
    if _state.get("json"):
        print_json(data)
        return
    status = data.get("status", {})
    print_detail([
        ("Hash", data.get("hash_value")),
        ("Active", data.get("is_active")),
        ("Status", status.get("status")),
        ("Results", status.get("total_results")),
        ("Pages", status.get("total_pages")),
        ("Done Reason", status.get("done_reason")),
        ("Errors", status.get("has_errors")),
        ("Params", data.get("params")),
    ])


@task_app.command("rm")
def delete_task(task_id: str = typer.Argument(..., help="Task hash")):
    """Delete a task."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delete(f"/tasks/{task_id}")
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted task {task_id[:12]}")
```

**Step 2: Register in cli.py:**

```python
from lobstr_cli.commands.task import task_app
app.add_typer(task_app, name="task", help="Task (input URL) management")
```

**Step 3: Commit**

```bash
git add src/lobstr_cli/commands/task.py src/lobstr_cli/cli.py
git commit -m "feat: task add, upload, upload-status, ls, show, rm commands"
```

---

### Task 10: Run Commands

**Files:**
- Create: `src/lobstr_cli/commands/run.py`
- Modify: `src/lobstr_cli/cli.py` (register run app)

**Step 1: Write run commands**

`src/lobstr_cli/commands/run.py`:
```python
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.config import resolve_alias
from lobstr_cli.display import (
    print_json, print_table, print_detail, print_success,
    print_info, print_error, make_progress, err_console,
)

run_app = typer.Typer(no_args_is_help=True)


def _resolve_squid(client, identifier: str) -> str:
    identifier = resolve_alias(identifier)
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    from lobstr_cli.resolve import match_hash_prefix
    return match_hash_prefix(identifier, items)


def _poll_run(client, run_id: str, download_path: str | None = None) -> dict:
    """Poll a run until completion, showing a progress bar."""
    with make_progress() as progress:
        task = progress.add_task("Running...", total=100)
        while True:
            stats = client.get(f"/runs/{run_id}/stats")
            total = stats.get("total_tasks", 0)
            done = stats.get("total_tasks_done", 0)
            is_done = stats.get("is_done", False)
            pct_str = stats.get("percent_done", "0%").replace("%", "")
            try:
                pct = float(pct_str)
            except ValueError:
                pct = 0
            progress.update(task, completed=pct, total=100,
                          description=f"Running... {done}/{total} tasks  ETA: {stats.get('eta', '?')}")
            if is_done:
                break
            time.sleep(3)

    run = client.get(f"/runs/{run_id}")
    if download_path:
        dl = client.get(f"/runs/{run_id}/download")
        s3_url = dl.get("s3", "")
        if s3_url:
            client.download(s3_url, download_path)
            print_success(f"Downloaded results to {download_path}")
    return run


@run_app.command("start")
def start_run(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    wait: bool = typer.Option(False, "--wait", help="Poll until run completes"),
    download: Optional[str] = typer.Option(None, "--download", help="Download CSV on completion (implies --wait)"),
):
    """Start a new run."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.post("/runs", json={"squid": squid_id})
    run_id = result.get("id", "")
    if _state.get("json") and not (wait or download):
        print_json(result)
        return
    print_success(f"Started run {run_id[:12]}")
    if download or wait:
        try:
            run = _poll_run(client, run_id, download_path=download)
        except KeyboardInterrupt:
            print_info(f"\nInterrupted. Resume with: lobstr run watch {run_id[:12]}")
            raise typer.Exit(0)
        if _state.get("json"):
            print_json(run)
            return
        print_detail([
            ("Status", run.get("status")),
            ("Results", run.get("total_results")),
            ("Duration", run.get("duration")),
            ("Credits", run.get("credit_used")),
            ("Done Reason", run.get("done_reason")),
        ])


@run_app.command("ls")
def list_runs(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    limit: int = typer.Option(20, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List runs for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    data = client.get("/runs", params={"squid": squid_id, "limit": limit, "page": page})
    if _state.get("json"):
        print_json(data)
        return
    items = data.get("data", [])
    rows = []
    for r in items:
        duration = r.get("duration")
        dur_str = f"{duration:.0f}s" if isinstance(duration, (int, float)) else str(duration or "—")
        rows.append([
            r.get("id", "")[:12],
            r.get("status", ""),
            str(r.get("total_results", "")),
            dur_str,
            str(r.get("credit_used", "")),
            r.get("done_reason", "") or "—",
        ])
    print_table(["Hash", "Status", "Results", "Duration", "Credits", "Reason"], rows)


@run_app.command("show")
def show_run(run_id: str = typer.Argument(..., help="Run hash or prefix")):
    """Show run details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get(f"/runs/{run_id}")
    if _state.get("json"):
        print_json(data)
        return
    print_detail([
        ("Hash", data.get("id")),
        ("Status", data.get("status")),
        ("Results", data.get("total_results")),
        ("Unique Results", data.get("total_unique_results")),
        ("Duration", data.get("duration")),
        ("Credits", data.get("credit_used")),
        ("Origin", data.get("origin")),
        ("Done Reason", data.get("done_reason")),
        ("Done Reason Desc", data.get("done_reason_desc")),
        ("Export Done", data.get("export_done")),
        ("Started At", data.get("started_at")),
        ("Ended At", data.get("ended_at")),
    ])


@run_app.command("stats")
def run_stats(run_id: str = typer.Argument(..., help="Run hash")):
    """Show run statistics."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get(f"/runs/{run_id}/stats")
    if _state.get("json"):
        print_json(data)
        return
    print_detail([
        ("Percent Done", data.get("percent_done")),
        ("Tasks", f"{data.get('total_tasks_done', 0)}/{data.get('total_tasks', 0)}"),
        ("Tasks Left", data.get("total_tasks_left")),
        ("Results", data.get("total_results")),
        ("Duration", data.get("duration")),
        ("ETA", data.get("eta")),
        ("Current Task", data.get("current_task")),
    ])


@run_app.command("tasks")
def run_tasks(
    run_id: str = typer.Argument(..., help="Run hash"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List tasks in a run."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get("/runtasks", params={"run": run_id, "limit": limit, "page": page})
    if _state.get("json"):
        print_json(data)
        return
    items = data.get("data", [])
    rows = []
    for t in items:
        params = t.get("params", {})
        url = params.get("url", str(params)[:50])
        rows.append([
            t.get("id", "")[:12],
            t.get("status", ""),
            str(t.get("total_results", "")),
            str(url)[:60],
            t.get("done_reason", "") or "—",
        ])
    print_table(["Hash", "Status", "Results", "URL/Params", "Reason"], rows)


@run_app.command("abort")
def abort_run(run_id: str = typer.Argument(..., help="Run hash")):
    """Abort a running run."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.post(f"/runs/{run_id}/abort")
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Aborted run {run_id[:12]}")


@run_app.command("download")
def download_run(
    run_id: str = typer.Argument(..., help="Run hash"),
    path: str = typer.Argument("results.csv", help="Output file path"),
):
    """Download run results as CSV."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    dl = client.get(f"/runs/{run_id}/download")
    if _state.get("json"):
        print_json(dl)
        return
    s3_url = dl.get("s3", "")
    if not s3_url:
        print_error("No download URL available. Run may not have finished exporting.")
        raise typer.Exit(1)
    client.download(s3_url, path)
    print_success(f"Downloaded to {path}")


@run_app.command("watch")
def watch_run(run_id: str = typer.Argument(..., help="Run hash")):
    """Live-poll run progress with progress bar."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    try:
        run = _poll_run(client, run_id)
    except KeyboardInterrupt:
        print_info("\nStopped watching.")
        raise typer.Exit(0)
    if _state.get("json"):
        print_json(run)
        return
    print_detail([
        ("Status", run.get("status")),
        ("Results", run.get("total_results")),
        ("Duration", run.get("duration")),
        ("Credits", run.get("credit_used")),
        ("Done Reason", run.get("done_reason")),
    ])
```

**Step 2: Register in cli.py:**

```python
from lobstr_cli.commands.run import run_app
app.add_typer(run_app, name="run", help="Run lifecycle management")
```

**Step 3: Commit**

```bash
git add src/lobstr_cli/commands/run.py src/lobstr_cli/cli.py
git commit -m "feat: run start, ls, show, stats, tasks, abort, download, watch commands"
```

---

### Task 11: The `go` Power Command

**Files:**
- Create: `src/lobstr_cli/commands/go.py`
- Modify: `src/lobstr_cli/cli.py` (register go command)

**Step 1: Write go command**

`src/lobstr_cli/commands/go.py`:
```python
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_success, print_info, print_error,
    make_progress, print_detail,
)

go_app = typer.Typer()


@go_app.command("go")
def go(
    crawler: str = typer.Argument(..., help="Crawler name or hash"),
    urls: Optional[list[str]] = typer.Argument(None, help="URLs to scrape"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File with URLs (one per line)"),
    param: Optional[list[str]] = typer.Option(None, "--param", "-p", help="KEY=VALUE, repeatable"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    output: str = typer.Option("results.csv", "--output", "-o", help="Output file path"),
    no_download: bool = typer.Option(False, "--no-download", help="Start run without waiting"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
):
    """Full workflow: create squid, add tasks, run, download."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()

    # 1. Resolve crawler
    print_info("Resolving crawler...")
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    from lobstr_cli.resolve import resolve_crawler
    crawler_id = resolve_crawler(crawler, items)
    crawler_name = next((c["name"] for c in items if c["id"] == crawler_id), crawler_id[:12])
    print_info(f"Using crawler: {crawler_name}")

    # 2. Gather URLs
    task_urls = list(urls) if urls else []
    if file:
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    task_urls.append(line)
    if not task_urls:
        print_error("No URLs provided. Pass URLs as arguments or use --file.")
        raise typer.Exit(1)

    squid_id = None
    run_id = None
    try:
        # 3. Create squid
        print_info(f"Creating squid ({len(task_urls)} tasks)...")
        body: dict = {"crawler": crawler_id}
        if name:
            body["name"] = name
        squid = client.post("/squids", json=body)
        squid_id = squid["id"]
        print_info(f"Squid: {squid.get('name')} ({squid_id[:12]})")

        # 4. Update squid params if needed
        update_body: dict = {}
        if concurrency is not None:
            update_body["concurrency"] = concurrency
        if param:
            params = {}
            for p in param:
                k, _, v = p.partition("=")
                params[k] = v
            update_body["params"] = params
        if update_body:
            client.post(f"/squids/{squid_id}", json=update_body)

        # 5. Add tasks
        tasks = [{"url": url} for url in task_urls]
        result = client.post("/tasks", json={"squid": squid_id, "tasks": tasks})
        created = result.get("tasks", [])
        dupes = result.get("duplicated_count", 0)
        print_info(f"Added {len(created)} tasks ({dupes} duplicates)")

        # 6. Start run
        run = client.post("/runs", json={"squid": squid_id})
        run_id = run["id"]
        print_info(f"Run started: {run_id[:12]}")

        if no_download:
            if _state.get("json"):
                print_json({"squid": squid_id, "run": run_id})
            else:
                print_success(f"Run {run_id[:12]} started. Watch with: lobstr run watch {run_id[:12]}")
            return

        # 7. Poll with progress
        with make_progress() as progress:
            task = progress.add_task("Running...", total=100)
            while True:
                stats = client.get(f"/runs/{run_id}/stats")
                total = stats.get("total_tasks", 0)
                done = stats.get("total_tasks_done", 0)
                is_done = stats.get("is_done", False)
                pct_str = stats.get("percent_done", "0%").replace("%", "")
                try:
                    pct = float(pct_str)
                except ValueError:
                    pct = 0
                progress.update(task, completed=pct, total=100,
                              description=f"Running... {done}/{total} tasks  ETA: {stats.get('eta', '?')}")
                if is_done:
                    break
                time.sleep(3)

        # 8. Download
        final = client.get(f"/runs/{run_id}")
        if _state.get("json"):
            print_json(final)
            return

        dl = client.get(f"/runs/{run_id}/download")
        s3_url = dl.get("s3", "")
        if s3_url:
            client.download(s3_url, output)
            print_success(f"Downloaded {final.get('total_results', '?')} results to {output}")
        else:
            print_info("No download available yet. Try: lobstr run download " + run_id[:12])

        print_detail([
            ("Status", final.get("status")),
            ("Results", final.get("total_results")),
            ("Duration", final.get("duration")),
            ("Credits", final.get("credit_used")),
        ])

    except KeyboardInterrupt:
        msg = "\nInterrupted."
        if squid_id:
            msg += f" Squid: {squid_id[:12]}"
        if run_id:
            msg += f" Run: {run_id[:12]}"
        print_info(msg)
        raise typer.Exit(0)
```

**Step 2: Register in cli.py:**

```python
from lobstr_cli.commands.go import go_app
app.registered_commands.extend(go_app.registered_commands)
```

**Step 3: Test manually**

Run: `lobstr go --help`
Expected: Shows go command help with all options

**Step 4: Commit**

```bash
git add src/lobstr_cli/commands/go.py src/lobstr_cli/cli.py
git commit -m "feat: go power command — full create-tasks-run-download workflow"
```

---

### Task 12: Results Command

**Files:**
- Create: `src/lobstr_cli/commands/results.py`
- Modify: `src/lobstr_cli/cli.py` (register results app)

**Step 1: Write results command**

`src/lobstr_cli/commands/results.py`:
```python
from __future__ import annotations

import json
from typing import Optional
import typer

from lobstr_cli.config import resolve_alias
from lobstr_cli.display import print_json, print_table, print_info

results_app = typer.Typer(no_args_is_help=True)


@results_app.command("get")
def get_results(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    format: str = typer.Option("json", "--format", help="Output format: json or csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to file"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(50, "--page-size"),
):
    """Fetch results for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid = resolve_alias(squid)
    # Resolve squid
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    from lobstr_cli.resolve import match_hash_prefix
    squid_id = match_hash_prefix(squid, items)

    data = client.get("/results", params={"squid": squid_id, "page": page, "page_size": page_size})

    if _state.get("json") or format == "json":
        if output:
            with open(output, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print_info(f"Saved to {output}")
        else:
            print_json(data)
        return

    # CSV format
    results = data.get("data", [])
    if not results:
        print_info("No results found.")
        return
    # Get all unique keys from results
    keys = list(dict.fromkeys(k for r in results for k in r.keys() if k not in ("id", "object", "squid", "run")))
    if output:
        import csv
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print_info(f"Saved {len(results)} rows to {output}")
    else:
        rows = [[str(r.get(k, ""))[:40] for k in keys[:8]] for r in results]
        print_table(keys[:8], rows)
```

**Step 2: Register in cli.py:**

```python
from lobstr_cli.commands.results import results_app
app.add_typer(results_app, name="results", help="Result fetching")
```

**Step 3: Commit**

```bash
git add src/lobstr_cli/commands/results.py src/lobstr_cli/cli.py
git commit -m "feat: results get command with JSON/CSV output"
```

---

### Task 13: Final Integration — Complete cli.py

**Files:**
- Modify: `src/lobstr_cli/cli.py`

**Step 1: Ensure cli.py has all registrations in the right order**

The final `cli.py` should have all imports at the bottom after the `main()` callback:

```python
from lobstr_cli.commands.auth import config_app, whoami_app
from lobstr_cli.commands.crawlers import crawlers_app
from lobstr_cli.commands.squid import squid_app
from lobstr_cli.commands.task import task_app
from lobstr_cli.commands.run import run_app
from lobstr_cli.commands.results import results_app
from lobstr_cli.commands.go import go_app

app.add_typer(config_app, name="config", help="Configuration management")
app.registered_commands.extend(whoami_app.registered_commands)
app.add_typer(crawlers_app, name="crawlers", help="Browse and search crawlers")
app.add_typer(squid_app, name="squid", help="Squid management")
app.add_typer(task_app, name="task", help="Task (input URL) management")
app.add_typer(run_app, name="run", help="Run lifecycle management")
app.add_typer(results_app, name="results", help="Result fetching")
app.registered_commands.extend(go_app.registered_commands)
```

**Step 2: Re-install and verify**

Run: `pip install -e ".[dev]"`
Run: `lobstr --help`
Expected: Shows all command groups: config, whoami, crawlers, squid, task, run, results, go

**Step 3: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: complete Phase 1-5 integration with all command groups"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Project scaffolding | pyproject.toml, __init__, __main__, conftest |
| 2 | Config module | config.py, test_config.py |
| 3 | HTTP client | client.py, test_client.py |
| 4 | Display module | display.py |
| 5 | Resolve module | resolve.py, test_resolve.py |
| 6 | Root CLI + auth | cli.py, commands/auth.py |
| 7 | Crawlers | commands/crawlers.py |
| 8 | Squid | commands/squid.py |
| 9 | Task | commands/task.py |
| 10 | Run | commands/run.py |
| 11 | Go command | commands/go.py |
| 12 | Results | commands/results.py |
| 13 | Final integration | cli.py cleanup |

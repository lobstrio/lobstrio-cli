from __future__ import annotations

import json as json_mod
from dataclasses import asdict
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_error, print_info
from lobstr_cli.resolve import resolve_account as _resolve_account

accounts_app = typer.Typer(no_args_is_help=True)


@accounts_app.command("ls")
def list_accounts():
    """List your accounts."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    items = client.accounts.list()
    if _state.get("json"):
        print_json([asdict(a) for a in items])
        return
    rows = []
    for a in items:
        rows.append([
            a.username,
            a.id[:12],
            a.type,
            a.status_code_info or "",
            (a.last_synchronization_time or "")[:10] or "—",
        ])
    print_table(["Username", "Hash", "Type", "Status", "Last Sync"], rows)


@accounts_app.command("show")
def show_account(account: str = typer.Argument(..., help="Account hash or username")):
    """Show account details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    account_id = _resolve_account(client, account)
    data = client.accounts.get(account_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    squid_names = ", ".join(s.get("name", "") for s in data.squids) if data.squids else "—"
    print_detail([
        ("Username", data.username),
        ("Hash", data.id),
        ("Type", data.type),
        ("Status", data.status_code_info),
        ("Status Detail", data.status_code_description),
        ("Base URL", data.baseurl),
        ("Created", data.created_at),
        ("Last Sync", data.last_synchronization_time),
        ("Updated", data.updated_at),
        ("Squids", squid_names),
    ])


@accounts_app.command("rm")
def delete_account(
    account: str = typer.Argument(..., help="Account hash or username"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an account permanently."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    account_id = _resolve_account(client, account)
    if not force:
        typer.confirm(f"Delete account {account_id[:12]}? This is permanent.", abort=True)
    result = client.accounts.delete(account_id)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted account {account_id[:12]}")


@accounts_app.command("types")
def list_account_types():
    """List available account types."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    items = client.accounts.types()
    if _state.get("json"):
        print_json([asdict(t) for t in items])
        return
    rows = []
    for t in items:
        cookie_names = ", ".join(c.get("name", "") for c in t.cookies) if t.cookies else "all session cookies"
        rows.append([
            t.name,
            t.domain,
            t.baseurl,
            cookie_names[:50],
        ])
    print_table(["Type", "Domain", "Base URL", "Required Cookies"], rows)


def _parse_cookies(
    cookie: list[str] | None,
    cookies_json: str | None,
    cookies_file: Path | None,
) -> dict:
    """Parse cookies from any of the three input methods."""
    result = {}
    if cookie:
        from lobstr_cli.resolve import parse_params
        result.update(parse_params(cookie))
    if cookies_json:
        result.update(json_mod.loads(cookies_json))
    if cookies_file:
        result.update(json_mod.loads(cookies_file.read_text()))
    if not result:
        print_error("No cookies provided. Use --cookie, --cookies-json, or --cookies-file")
        raise typer.Exit(1)
    return result


@accounts_app.command("sync")
def sync_account(
    type: str = typer.Argument(..., help="Account type (e.g. twitter-sync, facebook-sync)"),
    account: Optional[str] = typer.Option(None, "--account", help="Existing account hash to refresh"),
    cookie: Optional[list[str]] = typer.Option(None, "--cookie", "-c", help="Cookie KEY=VALUE, repeatable"),
    cookies_json: Optional[str] = typer.Option(None, "--cookies-json", help="Cookies as JSON string"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies-file", help="Path to cookies JSON file", exists=True),
):
    """Sync a new account or refresh cookies for an existing one."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    cookies = _parse_cookies(cookie, cookies_json, cookies_file)
    result = client.accounts.sync(type, cookies, account=account)
    if _state.get("json"):
        print_json(result)
        return
    sync_id = result.get("id", "")
    print_success(f"Sync started: {sync_id} (status: {result.get('status_text', '?')})")
    print_info(f"Check status with: lobstr accounts sync-status {sync_id}")


@accounts_app.command("sync-status")
def sync_status(sync_id: str = typer.Argument(..., help="Sync task ID")):
    """Check account sync status."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.accounts.sync_status(sync_id)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_detail([
        ("Sync ID", result.id),
        ("Status Code", result.status_code),
        ("Status", result.status_text),
        ("Account Hash", result.account_hash),
    ])


@accounts_app.command("update")
def update_account(
    account: str = typer.Argument(..., help="Account hash or username"),
    type: str = typer.Option(..., "--type", help="Account type (e.g. sales-nav-sync)"),
    param: Optional[list[str]] = typer.Option(None, "--param", help="Limit KEY=VALUE, repeatable"),
):
    """Update account limits."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    account_id = _resolve_account(client, account)
    if not param:
        print_error("No params specified. Use --param to set limits (e.g. --param batch=20)")
        raise typer.Exit(1)
    from lobstr_cli.resolve import parse_params
    result = client.accounts.update(account_id, type=type, params=parse_params(param))
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Updated limits for account {account_id[:12]}")

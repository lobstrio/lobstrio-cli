from __future__ import annotations

from dataclasses import asdict

import typer

from lobstr_cli.config import save_token, save_alias, load_config, get_config_path
from lobstr_cli.display import print_success, print_detail, print_json

config_app = typer.Typer(no_args_is_help=True)
whoami_app = typer.Typer()


@config_app.command("set-token")
def set_token(token: str = typer.Argument(..., help="Your Lobstr API token (get it at https://app.lobstr.io/dashboard/api)")):
    """Store your API token. Get your token at https://app.lobstr.io/dashboard/api"""
    save_token(token)
    print_success(f"Token saved to {get_config_path()}")


@config_app.command("show")
def show_config():
    """Show current configuration."""
    from lobstr_cli.cli import _state
    cfg = load_config()
    if _state.get("json"):
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


@config_app.command("set-alias")
def set_alias(
    name: str = typer.Argument(..., help="Alias name (used as @name)"),
    squid_id: str = typer.Argument(..., help="Squid hash to alias"),
):
    """Create an alias for a squid hash."""
    save_alias(name, squid_id)
    print_success(f"Alias @{name} -> {squid_id[:12]}")


@whoami_app.command("whoami")
def whoami():
    """Show current user and balance."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    me = client.me()
    balance = client.balance()
    if _state.get("json"):
        print_json({**asdict(me), "balance": asdict(balance)})
        return
    name = f"{me.first_name} {me.last_name}".strip() or None
    plan_name = me.plan[0].get("name") if me.plan else None
    plan_status = me.plan[0].get("status") if me.plan else None
    print_detail([
        ("Name", name),
        ("Email", me.email),
        ("Plan", plan_name),
        ("Status", plan_status),
        ("Staff", me.is_staff),
        ("Balance", f"{balance.available} credits"),
        ("Consumed", balance.consumed),
        ("Slots Used", f"{balance.used_slots}/{balance.total_available_slots}"),
    ])

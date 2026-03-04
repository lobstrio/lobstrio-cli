from __future__ import annotations

import typer

from lobstr_cli.config import save_token, load_config, get_config_path
from lobstr_cli.display import print_success, print_detail, print_json, print_error, print_table

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

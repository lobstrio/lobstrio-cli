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

from lobstr_cli.commands.crawlers import crawlers_app
app.add_typer(crawlers_app, name="crawlers", help="Browse and search crawlers")

from lobstr_cli.commands.squid import squid_app
app.add_typer(squid_app, name="squid", help="Squid management")

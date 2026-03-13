from __future__ import annotations

from typing import Optional
import typer

from lobstr_cli import __version__
from lobstrio import LobstrClient
from lobstr_cli.config import get_token
from lobstr_cli.display import set_output_mode, print_error

app = typer.Typer(
    name="lobstr",
    help="CLI for the Lobstr.io scraping API",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Shared state
_state: dict = {}


def get_client() -> LobstrClient:
    """Get or create the SDK client from global state."""
    if "client" not in _state:
        token = get_token(override=_state.get("token"))
        if not token:
            print_error("No API token. Run: lobstr config set-token <TOKEN>\n  Get your token at https://app.lobstr.io/dashboard/api")
            raise typer.Exit(1)
        client = LobstrClient(token=token)
        if _state.get("verbose"):
            import sys
            _orig_send = client._http._client.send
            def _verbose_send(request, **kwargs):
                resp = _orig_send(request, **kwargs)
                print(f"  {request.method} {request.url} -> {resp.status_code}", file=sys.stderr)
                return resp
            client._http._client.send = _verbose_send
        _state["client"] = client
    return _state["client"]


def _version_callback(value: bool):
    if value:
        typer.echo(f"lobstr {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    json: bool = typer.Option(False, "--json", help="Output raw JSON"),
    token: Optional[str] = typer.Option(None, "--token", envvar="LOBSTR_TOKEN", help="Override API token"),
    verbose: bool = typer.Option(False, "--verbose", help="Show request/response details"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-essential output"),
    version: bool = typer.Option(False, "--version", help="Show version", callback=_version_callback, is_eager=True),
):
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

from lobstr_cli.commands.task import task_app
app.add_typer(task_app, name="task", help="Task (input URL) management")

from lobstr_cli.commands.run import run_app
app.add_typer(run_app, name="run", help="Run lifecycle management")

from lobstr_cli.commands.go import go_app
app.registered_commands.extend(go_app.registered_commands)

from lobstr_cli.commands.results import results_app
app.add_typer(results_app, name="results", help="Result fetching")

from lobstr_cli.commands.accounts import accounts_app
app.add_typer(accounts_app, name="accounts", help="Account management")

from lobstr_cli.commands.delivery import delivery_app
app.add_typer(delivery_app, name="delivery", help="Delivery configuration")

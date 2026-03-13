from __future__ import annotations

from dataclasses import asdict
from typing import Optional
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_error
from lobstr_cli.resolve import resolve_squid as _resolve_squid

squid_app = typer.Typer(no_args_is_help=True)


@squid_app.command("create")
def create_squid(
    crawler: str = typer.Argument(..., help="Crawler hash, prefix, or name"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
):
    """Create a new squid for a crawler."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    all_crawlers = client.crawlers.list()
    from lobstr_cli.resolve import resolve_crawler
    crawler_id = resolve_crawler(crawler, all_crawlers)
    result = client.squids.create(crawler_id, name=name)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"Created squid: {result.name} ({result.id[:12]})")


@squid_app.command("ls")
def list_squids(
    name: Optional[str] = typer.Option(None, "--name", help="Filter by name"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List your squids."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    items = client.squids.list(limit=limit, page=page, name=name)
    if _state.get("json"):
        print_json([asdict(s) for s in items])
        return
    rows = []
    for s in items:
        rows.append([
            s.name,
            s.id[:12],
            s.crawler_name,
            "yes" if s.to_complete else "no",
            s.last_run_status or "—",
            str(s.concurrency),
        ])
    print_table(["Name", "Hash", "Crawler", "Pending", "Last Run", "Conc."], rows)


@squid_app.command("show")
def show_squid(squid: str = typer.Argument(..., help="Squid hash or prefix")):
    """Show squid details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    data = client.squids.get(squid_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    print_detail([
        ("Name", data.name),
        ("Hash", data.id),
        ("Crawler", data.crawler_name),
        ("Active", data.is_active),
        ("Ready", data.is_ready),
        ("Concurrency", data.concurrency),
        ("Pending Tasks", data.to_complete),
        ("Last Run", data.last_run_status),
        ("Last Run At", data.last_run_at),
        ("Total Runs", data.total_runs),
        ("Unique Results", data.export_unique_results),
        ("Params", data.params),
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
    kwargs: dict = {}
    if concurrency is not None:
        kwargs["concurrency"] = concurrency
    if name is not None:
        kwargs["name"] = name
    if notify is not None:
        kwargs["run_notify"] = None if notify == "null" else notify
    if unique_results is not None:
        kwargs["export_unique_results"] = unique_results
    if param:
        from lobstr_cli.resolve import parse_params
        kwargs["params"] = parse_params(param)
    if not kwargs:
        print_error("No options specified. Use --help to see available options.")
        raise typer.Exit(1)
    result = client.squids.update(squid_id, **kwargs)
    if _state.get("json"):
        print_json(asdict(result))
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
    result = client.squids.empty(squid_id, type=type)
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
    result = client.squids.delete(squid_id)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted squid {squid_id[:12]}")

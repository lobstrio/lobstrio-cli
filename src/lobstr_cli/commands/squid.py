from __future__ import annotations

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

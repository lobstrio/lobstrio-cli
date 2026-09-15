from __future__ import annotations

from dataclasses import asdict
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_table, print_detail, print_success, print_error, print_warning,
)
from lobstr_cli.resolve import resolve_squid as _resolve_squid

squid_app = typer.Typer(no_args_is_help=True)


@squid_app.command("create")
def create_squid(
    crawler: str = typer.Argument(..., help="Crawler hash, prefix, or name"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
):
    """Create a new squid for a crawler.

    The API doesn't accept `accounts` at creation time — for a crawler that
    needs a synced account (LinkedIn, Sales Navigator, ...), link one
    afterwards with `squid update SQUID --account ...`, or use `lobstr go`,
    which creates the squid and links an account in one command.
    """
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    from lobstr_cli.resolve import resolve_crawler_id
    crawler_id = resolve_crawler_id(client, crawler)
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


@squid_app.command("estimate")
def estimate_squid(squid: str = typer.Argument(..., help="Squid hash or prefix")):
    """Estimate the cost and results of running a squid (needs at least one task)."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    est = client.squids.estimate(squid_id)
    if _state.get("json"):
        print_json(est)
        return
    services = est.get("services") or []
    if services:
        rows = [[s.get("name"), str(s.get("results")), str(s.get("credits"))] for s in services]
        print_table(["Service", "Results", "Credits"], rows)
    tasks = est.get("tasks") or {}
    print_detail([
        ("Total Credits", est.get("total_credits")),
        ("Estimated Time", est.get("estimated_time") or "—"),
        ("Max Results", est.get("max_results")),
        ("Tasks", tasks.get("count")),
    ])
    rec = est.get("recommended_upgrade_plan")
    if rec:
        typer.echo(f"Not enough credits for this run — suggested plan: {rec.get('name')} (${rec.get('price')})")


@squid_app.command("update")
def update_squid(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency"),
    name: Optional[str] = typer.Option(None, "--name"),
    notify: Optional[str] = typer.Option(None, "--notify", help="on_success|on_error|null"),
    unique_results: Optional[bool] = typer.Option(None, "--unique-results/--no-unique-results"),
    param: Optional[list[str]] = typer.Option(None, "--param", help="KEY=VALUE, repeatable"),
    active: Optional[bool] = typer.Option(
        None, "--active/--inactive", help="Activate or deactivate the squid (frees its slot)"
    ),
    to_complete: Optional[int] = typer.Option(
        None, "--to-complete", help="Number of tasks queued to run"
    ),
    no_line_breaks: Optional[bool] = typer.Option(
        None, "--no-line-breaks/--line-breaks", help="Strip newlines from exported cells"
    ),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression to schedule runs"),
    timezone: Optional[str] = typer.Option(
        None, "--timezone", help="Timezone for the cron schedule, e.g. Europe/Paris"
    ),
    account: Optional[list[str]] = typer.Option(
        None, "--account",
        help="Account username or hash to link (repeatable). The API's `accounts` field is "
        "full-replace, so by default this is MERGED into the squid's existing accounts, "
        "never silently dropping one. Pass --replace-accounts to replace the whole list "
        "instead (e.g. with no --account at all, to detach everything).",
    ),
    replace_accounts: bool = typer.Option(
        False, "--replace-accounts",
        help="Replace the squid's account list with --account instead of merging into it.",
    ),
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
    if active is not None:
        kwargs["is_active"] = active
    if to_complete is not None:
        kwargs["to_complete"] = to_complete
    if no_line_breaks is not None:
        kwargs["no_line_breaks"] = no_line_breaks
    if cron is not None:
        kwargs["cron_expression"] = cron
    if timezone is not None:
        kwargs["timezone"] = timezone
    if not kwargs and not account and not replace_accounts:
        print_error("No options specified. Use --help to see available options.")
        raise typer.Exit(1)

    result = None
    if account or replace_accounts:
        from lobstr_cli.resolve import resolve_accounts_with_type_check
        current_squid = client.squids.get(squid_id)
        crawler = client.crawlers.get(current_squid.crawler)
        account_hashes = resolve_accounts_with_type_check(client, crawler, account or [])
        if replace_accounts:
            # The one destructive path in this command: --replace-accounts
            # sends exactly `account_hashes`, so anything currently attached
            # but not in that list is detached — including everything, when
            # --account was omitted entirely. Name what's about to be lost
            # before the call, not just report success afterwards.
            existing_ids = [a["id"] for a in current_squid.accounts]
            detached = [i for i in existing_ids if i not in account_hashes]
            if detached:
                print_warning(
                    f"Detaching {len(detached)} account(s) from squid {squid_id[:12]}: "
                    f"{', '.join(h[:12] for h in detached)}"
                )
        result = client.squids.attach_accounts(squid_id, account_hashes, replace=replace_accounts)
    if kwargs:
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

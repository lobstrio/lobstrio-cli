from __future__ import annotations

import time
from dataclasses import asdict
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_table, print_detail, print_success,
    print_info, print_error, make_progress,
)
from lobstr_cli.resolve import resolve_squid as _resolve_squid, require_full_hash

run_app = typer.Typer(no_args_is_help=True)


def _poll_run(client, run_id: str, download_path: str | None = None):
    """Poll a run until completion, showing a progress bar."""
    with make_progress() as progress:
        task = progress.add_task("Running...", total=100)
        while True:
            stats = client.runs.stats(run_id)
            pct_str = stats.percent_done.replace("%", "")
            try:
                pct = float(pct_str)
            except ValueError:
                pct = 0
            progress.update(task, completed=pct, total=100,
                          description=f"Running... {stats.total_tasks_done}/{stats.total_tasks} tasks  ETA: {stats.eta or '?'}")
            if stats.is_done:
                break
            time.sleep(3)

    run = client.runs.get(run_id)
    if download_path:
        try:
            client.runs.download(run_id, download_path)
            print_success(f"Downloaded results to {download_path}")
        except Exception:
            print_error("No download URL available. Run may not have finished exporting.")
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
    result = client.runs.start(squid=squid_id)
    if _state.get("json") and not (wait or download):
        print_json(asdict(result))
        return
    print_success(f"Started run {result.id}")
    if download or wait:
        try:
            run = _poll_run(client, result.id, download_path=download)
        except KeyboardInterrupt:
            print_info(f"\nInterrupted. Resume with: lobstr run watch {result.id}")
            raise typer.Exit(0)
        if _state.get("json"):
            print_json(asdict(run))
            return
        print_detail([
            ("Status", run.status),
            ("Results", run.total_results),
            ("Duration", run.duration),
            ("Credits", run.credit_used),
            ("Done Reason", run.done_reason),
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
    items = client.runs.list(squid=squid_id, limit=limit, page=page)
    if _state.get("json"):
        print_json([asdict(r) for r in items])
        return
    rows = []
    for r in items:
        dur_str = f"{r.duration:.0f}s" if isinstance(r.duration, (int, float)) else str(r.duration or "—")
        rows.append([
            r.id,
            r.status,
            str(r.total_results),
            dur_str,
            str(r.credit_used),
            r.done_reason or "—",
        ])
    print_table(["Hash", "Status", "Results", "Duration", "Credits", "Reason"], rows)


@run_app.command("show")
def show_run(run_id: str = typer.Argument(..., help="Full run hash")):
    """Show run details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    data = client.runs.get(run_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    print_detail([
        ("Hash", data.id),
        ("Status", data.status),
        ("Results", data.total_results),
        ("Unique Results", data.total_unique_results),
        ("Duration", data.duration),
        ("Credits", data.credit_used),
        ("Origin", data.origin),
        ("Done Reason", data.done_reason),
        ("Done Reason Desc", data.done_reason_desc),
        ("Export Done", data.export_done),
        ("Started At", data.started_at),
        ("Ended At", data.ended_at),
    ])


@run_app.command("stats")
def run_stats(run_id: str = typer.Argument(..., help="Full run hash")):
    """Show run statistics."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    data = client.runs.stats(run_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    print_detail([
        ("Percent Done", data.percent_done),
        ("Tasks", f"{data.total_tasks_done}/{data.total_tasks}"),
        ("Tasks Left", data.total_tasks_left),
        ("Results", data.total_results),
        ("Duration", data.duration),
        ("ETA", data.eta),
        ("Current Task", data.current_task),
    ])


@run_app.command("tasks")
def run_tasks(
    run_id: str = typer.Argument(..., help="Full run hash"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List tasks in a run."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    items = client.runs.tasks(run_id, limit=limit, page=page)
    if _state.get("json"):
        print_json([asdict(t) for t in items])
        return
    rows = []
    for t in items:
        url = t.params.get("url", str(t.params)[:50])
        status = t.status.status if t.status else "—"
        results = str(t.status.total_results) if t.status else ""
        done_reason = (t.status.done_reason if t.status else None) or "—"
        rows.append([
            t.id,
            status,
            results,
            str(url)[:60],
            done_reason,
        ])
    print_table(["Hash", "Status", "Results", "URL/Params", "Reason"], rows)


@run_app.command("abort")
def abort_run(run_id: str = typer.Argument(..., help="Full run hash")):
    """Abort a running run."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    result = client.runs.abort(run_id)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Aborted run {run_id}")


@run_app.command("download")
def download_run(
    run_id: str = typer.Argument(..., help="Full run hash"),
    path: str = typer.Argument("results.csv", help="Output file path"),
):
    """Download run results as CSV."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    if _state.get("json"):
        url = client.runs.download_url(run_id)
        print_json({"s3": url})
        return
    try:
        client.runs.download(run_id, path)
    except (KeyError, Exception):
        print_error("No download URL available. Run may not have finished exporting.")
        raise typer.Exit(1)
    print_success(f"Downloaded to {path}")


@run_app.command("watch")
def watch_run(run_id: str = typer.Argument(..., help="Full run hash")):
    """Live-poll run progress with progress bar."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(run_id, "run")
    try:
        run = _poll_run(client, run_id)
    except KeyboardInterrupt:
        print_info("\nStopped watching.")
        raise typer.Exit(0)
    if _state.get("json"):
        print_json(asdict(run))
        return
    print_detail([
        ("Status", run.status),
        ("Results", run.total_results),
        ("Duration", run.duration),
        ("Credits", run.credit_used),
        ("Done Reason", run.done_reason),
    ])

from __future__ import annotations

import time
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_table, print_detail, print_success,
    print_info, print_error, make_progress,
)
from lobstr_cli.resolve import resolve_squid as _resolve_squid

run_app = typer.Typer(no_args_is_help=True)


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

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_success, print_info, print_error,
    make_progress, print_detail,
)

go_app = typer.Typer()


def _find_squid_by_name(client, name: str, crawler_id: str):
    """Find an existing squid by name and crawler."""
    items = client.squids.list(name=name)
    for s in items:
        if s.name == name and s.crawler == crawler_id:
            return s
    return None


@go_app.command("go")
def go(
    crawler: str = typer.Argument(..., help="Crawler name or hash"),
    inputs: Optional[list[str]] = typer.Argument(None, help="URLs or keywords for tasks"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File with inputs (one per line)"),
    key: str = typer.Option("url", "--key", "-k", help="Task param name (url, keyword, etc.)"),
    param: Optional[list[str]] = typer.Option(None, "--param", "-p", help="KEY=VALUE, repeatable"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    output: str = typer.Option("results.csv", "--output", "-o", help="Output file path"),
    no_download: bool = typer.Option(False, "--no-download", help="Start run without waiting"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
    delete: bool = typer.Option(False, "--delete", help="Delete squid after completion"),
    empty: bool = typer.Option(False, "--empty", help="Empty old tasks before adding new ones (when reusing squid)"),
):
    """Full workflow: create squid, add tasks, run, download."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()

    # 1. Resolve crawler
    print_info("Resolving crawler...")
    all_crawlers = client.crawlers.list()
    from lobstr_cli.resolve import resolve_crawler
    crawler_id = resolve_crawler(crawler, all_crawlers)
    crawler_name = next((c.name for c in all_crawlers if c.id == crawler_id), crawler_id[:12])
    print_info(f"Using crawler: {crawler_name}")

    # 2. Gather inputs
    task_inputs = list(inputs) if inputs else []
    if file:
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    task_inputs.append(line)
    if not task_inputs:
        print_error("No inputs provided. Pass URLs/keywords as arguments or use --file.")
        raise typer.Exit(1)

    squid_id = None
    run_id = None
    created_new_squid = False
    try:
        # 3. Find existing or create squid
        existing = _find_squid_by_name(client, name, crawler_id) if name else None
        if existing:
            squid_id = existing.id
            print_info(f"Reusing squid: {existing.name} ({squid_id[:12]})")
            if empty:
                client.squids.empty(squid_id, type="url")
                print_info("Emptied old tasks")
        else:
            print_info(f"Creating squid ({len(task_inputs)} tasks)...")
            squid_obj = client.squids.create(crawler_id, name=name)
            squid_id = squid_obj.id
            created_new_squid = True
            print_info(f"Squid: {squid_obj.name} ({squid_id[:12]})")

        # 4. Update squid params if needed
        update_kwargs: dict = {}
        if concurrency is not None:
            update_kwargs["concurrency"] = concurrency
        if param:
            from lobstr_cli.resolve import parse_params
            update_kwargs["params"] = parse_params(param)
        if update_kwargs:
            client.squids.update(squid_id, **update_kwargs)

        # 5. Add tasks
        tasks = [{key: val} for val in task_inputs]
        result = client.tasks.add(squid=squid_id, tasks=tasks)
        print_info(f"Added {len(result.tasks)} tasks ({result.duplicated_count} duplicates)")

        # 6. Start run
        run = client.runs.start(squid=squid_id)
        run_id = run.id
        print_info(f"Run started: {run_id}")

        if no_download:
            if _state.get("json"):
                print_json({"squid": squid_id, "run": run_id})
            else:
                print_success(f"Run started. Watch with: lobstr run watch {run_id}")
            return

        # 7. Poll with progress
        with make_progress() as progress:
            ptask = progress.add_task("Running...", total=100)
            while True:
                stats = client.runs.stats(run_id)
                pct_str = stats.percent_done.replace("%", "")
                try:
                    pct = float(pct_str)
                except ValueError:
                    pct = 0
                progress.update(ptask, completed=pct, total=100,
                              description=f"Running... {stats.total_tasks_done}/{stats.total_tasks} tasks  ETA: {stats.eta or '?'}")
                if stats.is_done:
                    break
                time.sleep(3)

        # 8. Download (with retry — export may take a moment)
        final = client.runs.get(run_id)
        if _state.get("json"):
            print_json(asdict(final))
        else:
            downloaded = False
            for attempt in range(5):
                try:
                    client.runs.download(run_id, output)
                    downloaded = True
                    break
                except Exception:
                    pass
                if attempt == 0:
                    print_info("Waiting for export...")
                time.sleep(5)

            if downloaded:
                print_success(f"Downloaded {final.total_results} results to {output}")
            else:
                print_info("Export not ready. Try: lobstr run download " + run_id)

            print_detail([
                ("Status", final.status),
                ("Results", final.total_results),
                ("Duration", final.duration),
                ("Credits", final.credit_used),
            ])

        # 9. Delete squid if requested
        if delete:
            client.squids.delete(squid_id)
            print_info(f"Deleted squid {squid_id[:12]}")

    except KeyboardInterrupt:
        msg = "\nInterrupted."
        if squid_id:
            msg += f" Squid: {squid_id[:12]}"
        if run_id:
            msg += f" Run: {run_id}"
        print_info(msg)
        raise typer.Exit(0)
    except Exception:
        if created_new_squid and squid_id and not run_id:
            # Clean up orphaned squid if error before run started
            try:
                client.squids.delete(squid_id)
                print_info(f"Cleaned up squid {squid_id[:12]}")
            except Exception:
                print_info(f"Squid {squid_id[:12]} may need manual cleanup")
        raise

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_success, print_info, print_error,
    make_progress, print_detail,
)

go_app = typer.Typer()


@go_app.command("go")
def go(
    crawler: str = typer.Argument(..., help="Crawler name or hash"),
    urls: Optional[list[str]] = typer.Argument(None, help="URLs to scrape"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File with URLs (one per line)"),
    param: Optional[list[str]] = typer.Option(None, "--param", "-p", help="KEY=VALUE, repeatable"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    output: str = typer.Option("results.csv", "--output", "-o", help="Output file path"),
    no_download: bool = typer.Option(False, "--no-download", help="Start run without waiting"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
):
    """Full workflow: create squid, add tasks, run, download."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()

    # 1. Resolve crawler
    print_info("Resolving crawler...")
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    from lobstr_cli.resolve import resolve_crawler
    crawler_id = resolve_crawler(crawler, items)
    crawler_name = next((c["name"] for c in items if c["id"] == crawler_id), crawler_id[:12])
    print_info(f"Using crawler: {crawler_name}")

    # 2. Gather URLs
    task_urls = list(urls) if urls else []
    if file:
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    task_urls.append(line)
    if not task_urls:
        print_error("No URLs provided. Pass URLs as arguments or use --file.")
        raise typer.Exit(1)

    squid_id = None
    run_id = None
    try:
        # 3. Create squid
        print_info(f"Creating squid ({len(task_urls)} tasks)...")
        body: dict = {"crawler": crawler_id}
        if name:
            body["name"] = name
        squid = client.post("/squids", json=body)
        squid_id = squid["id"]
        print_info(f"Squid: {squid.get('name')} ({squid_id[:12]})")

        # 4. Update squid params if needed
        update_body: dict = {}
        if concurrency is not None:
            update_body["concurrency"] = concurrency
        if param:
            from lobstr_cli.resolve import parse_params
            update_body["params"] = parse_params(param)
        if update_body:
            client.post(f"/squids/{squid_id}", json=update_body)

        # 5. Add tasks
        tasks = [{"url": url} for url in task_urls]
        result = client.post("/tasks", json={"squid": squid_id, "tasks": tasks})
        created = result.get("tasks", [])
        dupes = result.get("duplicated_count", 0)
        print_info(f"Added {len(created)} tasks ({dupes} duplicates)")

        # 6. Start run
        run = client.post("/runs", json={"squid": squid_id})
        run_id = run["id"]
        print_info(f"Run started: {run_id[:12]}")

        if no_download:
            if _state.get("json"):
                print_json({"squid": squid_id, "run": run_id})
            else:
                print_success(f"Run {run_id[:12]} started. Watch with: lobstr run watch {run_id[:12]}")
            return

        # 7. Poll with progress
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

        # 8. Download
        final = client.get(f"/runs/{run_id}")
        if _state.get("json"):
            print_json(final)
            return

        dl = client.get(f"/runs/{run_id}/download")
        s3_url = dl.get("s3", "")
        if s3_url:
            client.download(s3_url, output)
            print_success(f"Downloaded {final.get('total_results', '?')} results to {output}")
        else:
            print_info("No download available yet. Try: lobstr run download " + run_id[:12])

        print_detail([
            ("Status", final.get("status")),
            ("Results", final.get("total_results")),
            ("Duration", final.get("duration")),
            ("Credits", final.get("credit_used")),
        ])

    except KeyboardInterrupt:
        msg = "\nInterrupted."
        if squid_id:
            msg += f" Squid: {squid_id[:12]}"
        if run_id:
            msg += f" Run: {run_id[:12]}"
        print_info(msg)
        raise typer.Exit(0)

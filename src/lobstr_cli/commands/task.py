from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_info, print_error
from lobstr_cli.resolve import resolve_squid as _resolve_squid

task_app = typer.Typer(no_args_is_help=True)


@task_app.command("add")
def add_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    values: list[str] = typer.Argument(..., help="URLs or keywords to add as tasks"),
    key: str = typer.Option("url", "--key", "-k", help="Task param name (url, keyword, etc.)"),
):
    """Add tasks to a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    tasks = [{key: v} for v in values]
    result = client.post("/tasks", json={"squid": squid_id, "tasks": tasks})
    if _state.get("json"):
        print_json(result)
        return
    created = result.get("tasks", [])
    dupes = result.get("duplicated_count", 0)
    print_success(f"Added {len(created)} tasks ({dupes} duplicates skipped)")


@task_app.command("upload")
def upload_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    file: Path = typer.Argument(..., help="CSV/TSV file path", exists=True),
):
    """Upload tasks from a CSV/TSV file."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    with open(file, "rb") as f:
        result = client.post("/tasks/upload", data={"squid": squid_id}, files={"file": (file.name, f)})
    if _state.get("json"):
        print_json(result)
        return
    upload_id = result.get("id", "")
    print_success(f"Upload started: {upload_id}")
    print_info(f"Check status with: lobstr task upload-status {upload_id}")


@task_app.command("upload-status")
def upload_status(upload_id: str = typer.Argument(..., help="Upload task ID")):
    """Check upload progress."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.get(f"/tasks/upload/{upload_id}")
    if _state.get("json"):
        print_json(result)
        return
    meta = result.get("meta", {})
    print_detail([
        ("State", result.get("state")),
        ("Valid", meta.get("valid")),
        ("Inserted", meta.get("inserted")),
        ("Duplicates", meta.get("duplicates")),
        ("Invalid", meta.get("invalid")),
    ])


@task_app.command("ls")
def list_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    limit: int = typer.Option(50, "--limit"),
    page: int = typer.Option(1, "--page"),
):
    """List tasks for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    data = client.get("/tasks", params={"squid": squid_id, "limit": limit, "page": page})
    if _state.get("json"):
        print_json(data)
        return
    items = data.get("data", [])
    rows = []
    for t in items:
        params = t.get("params", {})
        url = params.get("url", str(params)[:60])
        rows.append([
            t.get("id", "")[:12],
            "yes" if t.get("is_active") else "no",
            str(url)[:70],
            t.get("created_at", "")[:10],
        ])
    print_table(["Hash", "Active", "URL/Params", "Created"], rows)


@task_app.command("show")
def show_task(task_id: str = typer.Argument(..., help="Task hash")):
    """Show task details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get(f"/tasks/{task_id}")
    if _state.get("json"):
        print_json(data)
        return
    status = data.get("status", {})
    fields = [
        ("Hash", data.get("hash_value")),
        ("Active", data.get("is_active")),
    ]
    if isinstance(status, dict):
        fields.extend([
            ("Status", status.get("status")),
            ("Results", status.get("total_results")),
            ("Pages", status.get("total_pages")),
            ("Done Reason", status.get("done_reason")),
            ("Errors", status.get("has_errors")),
        ])
    else:
        fields.append(("Status", status[0] if isinstance(status, list) and status else status))
    fields.append(("Params", data.get("params")))
    print_detail(fields)


@task_app.command("rm")
def delete_task(task_id: str = typer.Argument(..., help="Task hash")):
    """Delete a task."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delete(f"/tasks/{task_id}")
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted task {task_id[:12]}")

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_success, print_info
from lobstr_cli.resolve import resolve_squid as _resolve_squid, require_full_hash

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
    result = client.tasks.add(squid=squid_id, tasks=tasks)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"Added {len(result.tasks)} tasks ({result.duplicated_count} duplicates skipped)")


@task_app.command("upload")
def upload_tasks(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    file: Path = typer.Argument(..., help="CSV/TSV file path", exists=True),
):
    """Upload tasks from a CSV/TSV file."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.tasks.upload(squid=squid_id, file=file)
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
    result = client.tasks.upload_status(upload_id)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_detail([
        ("State", result.state),
        ("Valid", result.meta.valid),
        ("Inserted", result.meta.inserted),
        ("Duplicates", result.meta.duplicates),
        ("Invalid", result.meta.invalid),
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
    items = client.tasks.list(squid=squid_id, limit=limit, page=page)
    if _state.get("json"):
        print_json([asdict(t) for t in items])
        return
    rows = []
    for t in items:
        url = t.params.get("url", str(t.params)[:60])
        rows.append([
            t.id,
            "yes" if t.is_active else "no",
            str(url)[:70],
            (t.created_at or "")[:10],
        ])
    print_table(["Hash", "Active", "URL/Params", "Created"], rows)


@task_app.command("show")
def show_task(task_id: str = typer.Argument(..., help="Full task hash")):
    """Show task details."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(task_id, "task")
    data = client.tasks.get(task_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    fields = [
        ("Hash", data.id),
        ("Active", data.is_active),
    ]
    if data.status:
        fields.extend([
            ("Status", data.status.status),
            ("Results", data.status.total_results),
            ("Pages", data.status.total_pages),
            ("Done Reason", data.status.done_reason),
            ("Errors", data.status.has_errors),
        ])
    fields.append(("Params", data.params))
    print_detail(fields)


@task_app.command("rm")
def delete_task(task_id: str = typer.Argument(..., help="Full task hash")):
    """Delete a task."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    require_full_hash(task_id, "task")
    result = client.tasks.delete(task_id)
    if _state.get("json"):
        print_json(result)
        return
    print_success(f"Deleted task {task_id}")

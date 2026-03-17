from __future__ import annotations

import json as json_mod
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

console = Console()
err_console = Console(stderr=True)

# Global state set by CLI callback
_json_mode = False
_quiet_mode = False


def set_output_mode(json_mode: bool = False, quiet: bool = False) -> None:
    global _json_mode, _quiet_mode
    _json_mode = json_mode
    _quiet_mode = quiet


def print_json(data: Any) -> None:
    console.print_json(json_mod.dumps(data, default=str))


def print_error(message: str) -> None:
    if _json_mode:
        print_json({"error": message})
    else:
        err_console.print(f"[bold red]Error:[/] {message}")


def print_success(message: str) -> None:
    if _quiet_mode:
        return
    if _json_mode:
        return
    err_console.print(f"[bold green]{message}[/]")


def print_info(message: str) -> None:
    if _quiet_mode:
        return
    if _json_mode:
        return
    err_console.print(f"[dim]{message}[/]")


def print_table(columns: list[str], rows: list[list[str]], title: str | None = None) -> None:
    table = Table(title=title, show_lines=False)
    for col in columns:
        if col in ("Hash", "Name", "Slug"):
            table.add_column(col, no_wrap=True)
        else:
            table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def print_detail(fields: list[tuple[str, Any]]) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    for name, value in fields:
        table.add_row(name, str(value) if value is not None else "[dim]—[/]")
    console.print(table)


def print_detail_grouped(sections: list[tuple[str | None, list[tuple[str, Any]]]]) -> None:
    """Print detail fields organized into labeled sections.

    Each section is a (title, fields) tuple. Title can be None for untitled sections.
    """

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    first = True
    for title, fields in sections:
        if not fields:
            continue
        if title:
            if not first:
                table.add_row("", "")
            table.add_row(f"[bold yellow]{title}[/]", "")
        for name, value in fields:
            table.add_row(name, str(value) if value is not None else "[dim]—[/]")
        first = False
    console.print(table)


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=err_console,
    )

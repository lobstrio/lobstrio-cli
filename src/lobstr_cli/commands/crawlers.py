from __future__ import annotations

from dataclasses import asdict
import typer

from lobstr_cli.display import print_json, print_table, print_detail_grouped, print_info

crawlers_app = typer.Typer(no_args_is_help=True)


@crawlers_app.command("ls")
def list_crawlers():
    """List all available crawlers."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    crawlers = client.crawlers.list()
    if _state.get("json"):
        print_json([asdict(c) for c in crawlers])
        return
    rows = []
    for c in crawlers:
        status = ""
        if c.has_issues:
            status = "[yellow]issues[/]"
        elif not c.is_available:
            status = "[red]unavailable[/]"
        elif c.is_premium:
            status = "[cyan]premium[/]"
        rows.append([
            c.name,
            c.slug,
            c.id[:12],
            str(c.credits_per_row or "?"),
            str(c.max_concurrency),
            "yes" if c.account else "no",
            status,
        ])
    print_table(["Name", "Slug", "Hash", "Credits/Row", "Max Conc.", "Needs Account", "Status"], rows)


@crawlers_app.command("show")
def show_crawler(crawler: str = typer.Argument(..., help="Crawler slug, hash, or name")):
    """Show crawler details."""
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    all_crawlers = client.crawlers.list()
    crawler_id = resolve_crawler(crawler, all_crawlers)
    data = client.crawlers.get(crawler_id)
    if _state.get("json"):
        print_json(asdict(data))
        return
    status = "available"
    if data.has_issues:
        status = "issues"
    elif not data.is_available:
        status = "unavailable"
    elif data.is_premium:
        status = "premium"
    sections = [
        (None, [
            ("Name", data.name),
            ("Slug", data.slug),
            ("Hash", data.id),
            ("Description", data.description),
            ("Status", status),
            ("Rank", data.rank),
        ]),
        ("Credits & Limits", [
            ("Credits/Row", data.credits_per_row),
            ("Credits/Email", data.credits_per_email),
            ("Max Concurrency", data.max_concurrency),
        ]),
        ("Flags", [
            ("Needs Account", "yes" if data.account else "no"),
            ("Email Verification", data.has_email_verification),
            ("Public", data.is_public),
            ("Premium", data.is_premium),
        ]),
    ]
    ws = data.default_worker_stats
    if ws:
        sections.append(("Worker Stats", [
            ("Success Ratio", ws.get("success_ratio")),
            ("Rate (min-max)", f"{ws.get('min_rate_per_worker', '?')}-{ws.get('max_rate_per_worker', '?')}"),
        ]))
    ews = data.email_worker_stats
    if ews:
        sections.append(("Email Worker Stats", [
            ("Success Ratio", ews.get("success_ratio")),
            ("Rate (min-max)", f"{ews.get('min_rate_per_worker', '?')}-{ews.get('max_rate_per_worker', '?')}"),
        ]))
    if data.result_fields:
        sections.append(("Result Fields", [
            ("Fields", ", ".join(data.result_fields)),
        ]))
    print_detail_grouped(sections)
    if data.input_params:
        print_info("\nInput Parameters:")
        input_rows = []
        for inp in data.input_params:
            input_rows.append([
                inp.get("name", ""),
                inp.get("level", ""),
                inp.get("type", ""),
                "yes" if inp.get("required") == "true" else "no",
                str(inp.get("default", "")),
            ])
        print_table(["Name", "Level", "Type", "Required", "Default"], input_rows)


@crawlers_app.command("params")
def crawler_params(crawler: str = typer.Argument(..., help="Crawler hash or prefix")):
    """Show parameters for a crawler."""
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    all_crawlers = client.crawlers.list()
    crawler_id = resolve_crawler(crawler, all_crawlers)
    params = client.crawlers.params(crawler_id)
    if _state.get("json"):
        print_json(asdict(params))
        return
    if params.task_params:
        print_info("Task-level parameters:")
        rows = []
        for name, spec in params.task_params.items():
            rows.append([
                name,
                spec.get("type", ""),
                "yes" if spec.get("required") else "no",
                str(spec.get("default", "")),
                spec.get("regex", ""),
            ])
        print_table(["Name", "Type", "Required", "Default", "Regex"], rows)
    if params.squid_params:
        print_info("\nSquid-level parameters:")
        rows = []
        for name, spec in params.squid_params.items():
            allowed = ", ".join(str(v) for v in spec["allowed"]) if isinstance(spec.get("allowed"), list) else ""
            rows.append([
                name,
                str(spec.get("default", "")),
                "yes" if spec.get("required") else "no",
                allowed[:50],
            ])
        print_table(["Name", "Default", "Required", "Allowed Values"], rows)
    if params.functions:
        print_info("\nOptional functions (extra credits):")
        rows = []
        for name, spec in params.functions.items():
            cpf = spec.get("credits_per_function", "")
            if isinstance(cpf, dict):
                cpf = cpf.get("current", cpf.get("legacy", ""))
            rows.append([name, str(cpf), str(spec.get("default", ""))])
        print_table(["Function", "Credits", "Default"], rows)


@crawlers_app.command("attrs")
def crawler_attributes(crawler: str = typer.Argument(..., help="Crawler slug, hash, or name")):
    """Show result attributes (columns) for a crawler."""
    from collections import OrderedDict
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    all_crawlers = client.crawlers.list()
    crawler_id = resolve_crawler(crawler, all_crawlers)
    attrs = client.crawlers.attributes(crawler_id)
    if _state.get("json"):
        print_json([asdict(a) for a in attrs])
        return
    if not attrs:
        print_info("No attributes found for this crawler.")
        return
    groups: OrderedDict[str, list] = OrderedDict()
    for a in attrs:
        groups.setdefault(a.function, []).append(a)
    for func, items in groups.items():
        print_info(f"\n{func}:")
        rows = []
        for a in items:
            example = str(a.example) if a.example is not None else ""
            if len(example) > 40:
                example = example[:40] + "..."
            type_colors = {
                "string": "green", "text": "green",
                "integer": "cyan", "float": "cyan",
                "boolean": "yellow",
                "json": "magenta",
            }
            color = type_colors.get(a.type, "")
            if example and color:
                example = f"[{color}]{example}[/]"
            rows.append([
                f"[bold]{a.name}[/]",
                a.type,
                "[green]yes[/]" if a.is_main else "no",
                a.description,
                example,
            ])
        print_table(["Name", "Type", "Main", "Description", "Example"], rows)


@crawlers_app.command("search")
def search_crawlers(keyword: str = typer.Argument(..., help="Search keyword")):
    """Search crawlers by name."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    crawlers = client.crawlers.list()
    lower = keyword.lower()
    matches = [c for c in crawlers if lower in c.name.lower()]
    if _state.get("json"):
        print_json([asdict(c) for c in matches])
        return
    if not matches:
        print_info(f"No crawlers matching '{keyword}'")
        return
    rows = []
    for c in matches:
        status = ""
        if c.has_issues:
            status = "[yellow]issues[/]"
        elif not c.is_available:
            status = "[red]unavailable[/]"
        elif c.is_premium:
            status = "[cyan]premium[/]"
        rows.append([
            c.name,
            c.slug,
            c.id[:12],
            str(c.credits_per_row or "?"),
            str(c.max_concurrency),
            "yes" if c.account else "no",
            status,
        ])
    print_table(["Name", "Slug", "Hash", "Credits/Row", "Max Conc.", "Needs Account", "Status"], rows)

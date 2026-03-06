from __future__ import annotations

from typing import Optional
import typer

from lobstr_cli.display import print_json, print_table, print_detail, print_detail_grouped, print_info

crawlers_app = typer.Typer(no_args_is_help=True)


@crawlers_app.command("ls")
def list_crawlers():
    """List all available crawlers."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get("/crawlers")
    items = data.get("data", data) if isinstance(data, dict) else data
    if _state.get("json"):
        print_json(data)
        return
    rows = []
    for c in items:
        status = ""
        if c.get("has_issues"):
            status = "[yellow]issues[/]"
        elif not c.get("is_available"):
            status = "[red]unavailable[/]"
        elif c.get("is_premium"):
            status = "[cyan]premium[/]"
        cpr = c.get("credits_per_row", "?")
        if isinstance(cpr, dict):
            cpr = cpr.get("current", cpr.get("legacy", "?"))
        rows.append([
            c.get("name", ""),
            c.get("slug", ""),
            c.get("id", "")[:12],
            str(cpr),
            str(c.get("max_concurrency", "")),
            "yes" if c.get("account") else "no",
            status,
        ])
    print_table(["Name", "Slug", "Hash", "Credits/Row", "Max Conc.", "Needs Account", "Status"], rows)


@crawlers_app.command("show")
def show_crawler(crawler: str = typer.Argument(..., help="Crawler slug, hash, or name")):
    """Show crawler details."""
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    crawler_id = resolve_crawler(crawler, items)
    data = next(c for c in items if c["id"] == crawler_id)
    if _state.get("json"):
        print_json(data)
        return
    cpr = data.get("credits_per_row", "?")
    if isinstance(cpr, dict):
        cpr = cpr.get("current", cpr.get("legacy", "?"))
    status = "available"
    if data.get("has_issues"):
        status = "issues"
    elif not data.get("is_available"):
        status = "unavailable"
    elif data.get("is_premium"):
        status = "premium"
    cpe = data.get("credits_per_email", "?")
    if isinstance(cpe, dict):
        cpe = cpe.get("current", cpe.get("legacy", "?"))
    sections = [
        (None, [
            ("Name", data.get("name")),
            ("Slug", data.get("slug")),
            ("Hash", data.get("id")),
            ("Description", data.get("description")),
            ("Status", status),
            ("Rank", data.get("rank")),
        ]),
        ("Credits & Limits", [
            ("Credits/Row", cpr),
            ("Credits/Email", cpe),
            ("Max Concurrency", data.get("max_concurrency")),
        ]),
        ("Flags", [
            ("Needs Account", "yes" if data.get("account") else "no"),
            ("Email Verification", data.get("has_email_verification")),
            ("Public", data.get("is_public")),
            ("Premium", data.get("is_premium")),
        ]),
    ]
    ws = data.get("default_worker_stats")
    if ws:
        sections.append(("Worker Stats", [
            ("Success Ratio", ws.get("success_ratio")),
            ("Rate (min-max)", f"{ws.get('min_rate_per_worker', '?')}-{ws.get('max_rate_per_worker', '?')}"),
        ]))
    ews = data.get("email_worker_stats")
    if ews:
        sections.append(("Email Worker Stats", [
            ("Success Ratio", ews.get("success_ratio")),
            ("Rate (min-max)", f"{ews.get('min_rate_per_worker', '?')}-{ews.get('max_rate_per_worker', '?')}"),
        ]))
    print_detail_grouped(sections)


@crawlers_app.command("params")
def crawler_params(crawler: str = typer.Argument(..., help="Crawler hash or prefix")):
    """Show parameters for a crawler."""
    from lobstr_cli.cli import get_client, _state
    from lobstr_cli.resolve import resolve_crawler
    client = get_client()
    # Resolve crawler
    all_crawlers = client.get("/crawlers")
    items = all_crawlers.get("data", all_crawlers) if isinstance(all_crawlers, dict) else all_crawlers
    crawler_id = resolve_crawler(crawler, items)
    data = client.get(f"/crawlers/{crawler_id}/params")
    if _state.get("json"):
        print_json(data)
        return
    # Task-level params
    task_params = data.get("task", {})
    if task_params:
        print_info("Task-level parameters:")
        rows = []
        for name, spec in task_params.items():
            rows.append([
                name,
                spec.get("type", ""),
                "yes" if spec.get("required") else "no",
                str(spec.get("default", "")),
                spec.get("regex", ""),
            ])
        print_table(["Name", "Type", "Required", "Default", "Regex"], rows)
    # Squid-level params
    squid_params = data.get("squid", {})
    funcs = squid_params.pop("functions", {}) if isinstance(squid_params, dict) else {}
    if squid_params:
        print_info("\nSquid-level parameters:")
        rows = []
        for name, spec in squid_params.items():
            if name == "functions":
                continue
            allowed = ", ".join(str(v) for v in spec["allowed"]) if isinstance(spec.get("allowed"), list) else ""
            rows.append([
                name,
                str(spec.get("default", "")),
                "yes" if spec.get("required") else "no",
                allowed[:50],
            ])
        print_table(["Name", "Default", "Required", "Allowed Values"], rows)
    if funcs:
        print_info("\nOptional functions (extra credits):")
        rows = []
        for name, spec in funcs.items():
            cpf = spec.get("credits_per_function", "")
            if isinstance(cpf, dict):
                cpf = cpf.get("current", cpf.get("legacy", ""))
            rows.append([name, str(cpf), str(spec.get("default", ""))])
        print_table(["Function", "Credits", "Default"], rows)


@crawlers_app.command("search")
def search_crawlers(keyword: str = typer.Argument(..., help="Search keyword")):
    """Search crawlers by name."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    data = client.get("/crawlers")
    items = data.get("data", data) if isinstance(data, dict) else data
    lower = keyword.lower()
    matches = [c for c in items if lower in c.get("name", "").lower()]
    if _state.get("json"):
        print_json(matches)
        return
    if not matches:
        print_info(f"No crawlers matching '{keyword}'")
        return
    rows = []
    for c in matches:
        cpr = c.get("credits_per_row", "?")
        if isinstance(cpr, dict):
            cpr = cpr.get("current", cpr.get("legacy", "?"))
        rows.append([c.get("name", ""), c.get("id", "")[:12], str(cpr)])
    print_table(["Name", "Hash", "Credits/Row"], rows)

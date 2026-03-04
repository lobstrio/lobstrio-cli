from __future__ import annotations

import json
from typing import Optional
import typer

from lobstr_cli.config import resolve_alias
from lobstr_cli.display import print_json, print_table, print_info

results_app = typer.Typer(no_args_is_help=True)


@results_app.command("get")
def get_results(
    squid: str = typer.Argument(..., help="Squid hash or prefix"),
    format: str = typer.Option("json", "--format", help="Output format: json or csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to file"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(50, "--page-size"),
):
    """Fetch results for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid = resolve_alias(squid)
    # Resolve squid
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    from lobstr_cli.resolve import match_hash_prefix
    squid_id = match_hash_prefix(squid, items)

    data = client.get("/results", params={"squid": squid_id, "page": page, "page_size": page_size})

    if _state.get("json") or format == "json":
        if output:
            with open(output, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print_info(f"Saved to {output}")
        else:
            print_json(data)
        return

    # CSV format
    results = data.get("data", [])
    if not results:
        print_info("No results found.")
        return
    # Get all unique keys from results
    keys = list(dict.fromkeys(k for r in results for k in r.keys() if k not in ("id", "object", "squid", "run")))
    if output:
        import csv
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print_info(f"Saved {len(results)} rows to {output}")
    else:
        rows = [[str(r.get(k, ""))[:40] for k in keys[:8]] for r in results]
        print_table(keys[:8], rows)

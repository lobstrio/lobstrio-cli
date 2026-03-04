from __future__ import annotations

from lobstr_cli.display import print_error


def match_hash_prefix(prefix: str, items: list[dict], key: str = "id") -> str:
    # Exact match first
    for item in items:
        if item[key] == prefix:
            return prefix
    matches = [item[key] for item in items if item[key].startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        print_error(f"No match for prefix '{prefix}'")
        raise SystemExit(1)
    print_error(f"Ambiguous prefix '{prefix}' matches: {', '.join(matches[:5])}")
    raise SystemExit(1)


def resolve_squid(client, identifier: str) -> str:
    """Resolve a squid alias or hash prefix to a full squid ID."""
    from lobstr_cli.config import resolve_alias
    identifier = resolve_alias(identifier)
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    return match_hash_prefix(identifier, items)


def match_crawler_name(name: str, crawlers: list[dict]) -> str:
    lower = name.lower()
    # Exact match first
    for c in crawlers:
        if c["name"].lower() == lower:
            return c["id"]
    # Substring match
    matches = [c for c in crawlers if lower in c["name"].lower()]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) == 0:
        print_error(f"No crawler matching '{name}'")
        raise SystemExit(1)
    names = [m["name"] for m in matches[:5]]
    print_error(f"Ambiguous name '{name}' matches: {', '.join(names)}")
    raise SystemExit(1)


def resolve_crawler(identifier: str, crawlers: list[dict]) -> str:
    """Resolve a crawler identifier that could be a hash, prefix, or name."""
    # If it looks like a hex hash/prefix, try hash matching first
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), crawlers)
        except SystemExit:
            pass
    # Fall back to name matching
    return match_crawler_name(identifier, crawlers)

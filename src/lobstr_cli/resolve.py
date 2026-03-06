from __future__ import annotations

from lobstr_cli.display import print_error


def require_full_hash(value: str, label: str = "resource") -> None:
    """Raise a clear error if a partial hash is given for run/task endpoints."""
    if len(value) < 32:
        print_error(
            f"The API requires a full 32-character hash for {label}s. "
            f"Got {len(value)} characters: '{value}'. "
            f"Use `lobstr run ls` or `lobstr task ls` to get full hashes."
        )
        raise SystemExit(1)


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


def match_slug(slug: str, items: list[dict], label: str = "squid") -> str:
    """Match by slug field: exact first, then prefix, error on ambiguous."""
    lower = slug.lower()
    # Exact slug match
    for item in items:
        if item.get("slug", "").lower() == lower:
            return item["id"]
    # Prefix slug match
    matches = [item for item in items if item.get("slug", "").lower().startswith(lower)]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) == 0:
        print_error(f"No {label} matching slug '{slug}'")
        raise SystemExit(1)
    names = [m.get("slug", m.get("name", "")) for m in matches[:5]]
    print_error(f"Ambiguous {label} slug '{slug}' matches: {', '.join(names)}")
    raise SystemExit(1)


def match_name(name: str, items: list[dict], label: str = "squid") -> str:
    """Match by name: exact first, then substring, error on ambiguous."""
    lower = name.lower()
    for item in items:
        if item.get("name", "").lower() == lower:
            return item["id"]
    matches = [item for item in items if lower in item.get("name", "").lower()]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) == 0:
        print_error(f"No {label} matching '{name}'")
        raise SystemExit(1)
    names = [m["name"] for m in matches[:5]]
    print_error(f"Ambiguous {label} name '{name}' matches: {', '.join(names)}")
    raise SystemExit(1)


def resolve_squid(client, identifier: str) -> str:
    """Resolve a squid by alias, hash, or name."""
    from lobstr_cli.config import resolve_alias
    identifier = resolve_alias(identifier)
    all_squids = client.get("/squids")
    items = all_squids.get("data", [])
    # 1. Hash: if all hex chars, try hash prefix match
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), items)
        except SystemExit:
            pass
    # 2. Name: fallback to name match
    return match_name(identifier, items, "squid")


def match_crawler_name(name: str, crawlers: list[dict]) -> str:
    return match_name(name, crawlers, "crawler")


def resolve_crawler(identifier: str, crawlers: list[dict]) -> str:
    """Resolve a crawler by hash, slug, or name."""
    # 1. Hash: if all hex chars, try hash prefix match
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), crawlers)
        except SystemExit:
            pass
    # 2. Slug: if contains dashes, try slug match
    if "-" in identifier:
        return match_slug(identifier, crawlers, "crawler")
    # 3. Name: fallback to name match
    return match_crawler_name(identifier, crawlers)


def parse_param_value(value: str):
    """Coerce string param values to appropriate types."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() == "none":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def parse_params(param_list: list[str]) -> dict:
    """Parse KEY=VALUE pairs into a dict with type coercion."""
    params = {}
    for p in param_list:
        k, _, v = p.partition("=")
        params[k] = parse_param_value(v)
    return params



from __future__ import annotations

from typing import Any

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


def match_hash_prefix(prefix: str, items: list[Any], key: str = "id") -> str:
    """Match by hash prefix. Items can be dicts or model objects."""
    def _get(item: Any, k: str) -> str:
        return item[k] if isinstance(item, dict) else getattr(item, k)

    for item in items:
        if _get(item, key) == prefix:
            return prefix
    matches = [_get(item, key) for item in items if _get(item, key).startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        print_error(f"No match for prefix '{prefix}'")
        raise SystemExit(1)
    print_error(f"Ambiguous prefix '{prefix}' matches: {', '.join(matches[:5])}")
    raise SystemExit(1)


def _attr(item: Any, name: str, default: str = "") -> str:
    """Get attribute from model object or dict."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def match_slug(slug: str, items: list[Any], label: str = "squid") -> str:
    lower = slug.lower()
    for item in items:
        if _attr(item, "slug").lower() == lower:
            return _attr(item, "id")
    matches = [item for item in items if _attr(item, "slug").lower().startswith(lower)]
    if len(matches) == 1:
        return _attr(matches[0], "id")
    if len(matches) == 0:
        print_error(f"No {label} matching slug '{slug}'")
        raise SystemExit(1)
    names = [_attr(m, "slug") or _attr(m, "name") for m in matches[:5]]
    print_error(f"Ambiguous {label} slug '{slug}' matches: {', '.join(names)}")
    raise SystemExit(1)


def match_name(name: str, items: list[Any], label: str = "squid") -> str:
    lower = name.lower()
    for item in items:
        if _attr(item, "name").lower() == lower:
            return _attr(item, "id")
    matches = [item for item in items if lower in _attr(item, "name").lower()]
    if len(matches) == 1:
        return _attr(matches[0], "id")
    if len(matches) == 0:
        print_error(f"No {label} matching '{name}'")
        raise SystemExit(1)
    names = [_attr(m, "name") for m in matches[:5]]
    print_error(f"Ambiguous {label} name '{name}' matches: {', '.join(names)}")
    raise SystemExit(1)


def resolve_squid(client, identifier: str) -> str:
    from lobstr_cli.config import resolve_alias
    identifier = resolve_alias(identifier)
    items = client.squids.list()
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), items)
        except SystemExit:
            pass
    return match_name(identifier, items, "squid")


def match_username(username: str, items: list[Any], label: str = "account") -> str:
    lower = username.lower()
    for item in items:
        if _attr(item, "username").lower() == lower:
            return _attr(item, "id")
    matches = [item for item in items if lower in _attr(item, "username").lower()]
    if len(matches) == 1:
        return _attr(matches[0], "id")
    if len(matches) == 0:
        print_error(f"No {label} matching username '{username}'")
        raise SystemExit(1)
    names = [_attr(m, "username") for m in matches[:5]]
    print_error(f"Ambiguous {label} username '{username}' matches: {', '.join(names)}")
    raise SystemExit(1)


def resolve_account(client, identifier: str) -> str:
    items = client.accounts.list()
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), items)
        except SystemExit:
            pass
    return match_username(identifier, items, "account")


def match_crawler_name(name: str, crawlers: list[Any]) -> str:
    return match_name(name, crawlers, "crawler")


def resolve_crawler(identifier: str, crawlers: list[Any]) -> str:
    if all(c in "0123456789abcdef" for c in identifier.lower()):
        try:
            return match_hash_prefix(identifier.lower(), crawlers)
        except SystemExit:
            pass
    if "-" in identifier:
        return match_slug(identifier, crawlers, "crawler")
    return match_crawler_name(identifier, crawlers)


def parse_param_value(value: str):
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
    params = {}
    for p in param_list:
        k, _, v = p.partition("=")
        params[k] = parse_param_value(v)
    return params

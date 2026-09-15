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


FULL_HASH_LEN = 32


def _is_hex(value: str) -> bool:
    return bool(value) and all(c in "0123456789abcdef" for c in value.lower())


def fetch_crawlers(client) -> list[Any]:
    """Fetch the whole crawler catalog.

    ``crawlers.list()`` returns a single page (50 of ~183), so anything past
    page 1 is invisible to it. The catalog has no server-side search and the
    API caps ``limit`` at 120, so walking every page is the only way to see it
    all.
    """
    return list(client.crawlers.iter())


def resolve_crawler_id(client, identifier: str) -> str:
    """Resolve a crawler identifier to its hash.

    A complete 32-character hash is used as-is: the API can serve it directly,
    so there is no reason to walk the catalog to confirm it exists (and a hash
    for a crawler past page 1 used to be rejected for that reason). A wrong
    hash surfaces as a clean API error. Anything else — slug, name, prefix —
    needs the catalog, which is fetched lazily.
    """
    if len(identifier) == FULL_HASH_LEN and _is_hex(identifier):
        return identifier.lower()
    return resolve_crawler(identifier, fetch_crawlers(client))


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
    items = list(client.squids.iter())
    if _is_hex(identifier):
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
    items = list(client.accounts.iter())
    if _is_hex(identifier):
        try:
            return match_hash_prefix(identifier.lower(), items)
        except SystemExit:
            pass
    return match_username(identifier, items, "account")


def resolve_accounts_with_type_check(client, crawler: Any, identifiers: list[str]) -> list[str]:
    """Resolve `--account` values to hashes and enforce the crawler's account
    type before any of them reach the API.

    The API answers a wrong-type account, an unknown hash, and someone else's
    account with the *same* 404 (`AccountDoesNotExist`, rewritten to
    `HTTPNotFound` — see docs/agents/api/squids.md), and a crawler that needs
    no account with a generic `InvalidParam("accounts")`, 400. None of that is
    something a user can act on. Checking the type client-side, against data
    already fetched to resolve the identifier, turns both into a specific
    message before the request is even sent.

    Fetches the account list **once** and resolves every identifier against
    that same snapshot (mirroring `resolve_account`'s own hash-prefix-then-
    username logic, rather than calling it — calling it would re-fetch per
    identifier, and a second listing that disagreed with the first, e.g. a
    paginated result changing between calls, could return a hash the first
    snapshot has no record of, silently skipping the type check below instead
    of failing it). "Unknown hash"/"unknown username" is the same "No
    account matching ..." error `resolve_account()` raises, from the same
    `match_hash_prefix`/`match_username` helpers.

    `identifiers` empty is always a no-op (returns `[]`), whether or not the
    crawler needs an account — this is what lets `go` call this unconditionally
    right after resolving the crawler, before creating anything.
    """
    if not identifiers:
        return []
    if not crawler.account_type:
        print_error(
            f"{crawler.name} does not use an account; drop --account "
            f"(got: {', '.join(identifiers)})."
        )
        raise SystemExit(1)
    items = list(client.accounts.iter())
    by_id = {_attr(a, "id"): a for a in items}
    hashes = []
    for ident in identifiers:
        if _is_hex(ident):
            try:
                account_hash = match_hash_prefix(ident.lower(), items)
            except SystemExit:
                account_hash = match_username(ident, items, "account")
        else:
            account_hash = match_username(ident, items, "account")
        account = by_id[account_hash]
        if _attr(account, "type") != crawler.account_type:
            print_error(
                f"Account '{_attr(account, 'username')}' is a {_attr(account, 'type')} "
                f"account; {crawler.name} needs a {crawler.account_type} account. Run "
                f"`lobstr accounts ls` to see what you have, or "
                f"`lobstr accounts sync {crawler.account_type} ...` to connect one."
            )
            raise SystemExit(1)
        hashes.append(account_hash)
    return hashes


def healthy_account_candidates(client, crawler: Any) -> list[Any]:
    """Accounts eligible for auto-pick: exact `account_type` match, `status`
    ``"200"``, **not** `status_code_info == "cookies_expired"`, and no live
    lock (`resets_in` unset or `<= 0`) — the full condition
    `matrix/worker/consumer.py` uses to accept an attached account, all four
    of which must hold, not `status` alone. `lobstr-mcp`'s
    `account_linking.is_healthy()` implements the same condition (from
    `lock_time` rather than `resets_in` — the API's `resets_in` is that same
    lock re-expressed as seconds remaining); the two clients must not drift
    on this, since a candidate either client picks has to actually run.

    Matching on `crawler.account_type` rather than the crawler's name is
    deliberate: two LinkedIn crawlers can need two different account types
    (`linkedin-sync` vs `sales-nav-sync`), and the wrong one attaches "fine"
    client-side only to fail the run later.
    """
    return [
        a for a in client.accounts.iter()
        if a.type == crawler.account_type
        and a.status == "200"
        and (a.status_code_info or "") != "cookies_expired"
        and not (a.resets_in and a.resets_in > 0)
    ]


def match_crawler_name(name: str, crawlers: list[Any]) -> str:
    return match_name(name, crawlers, "crawler")


def resolve_crawler(identifier: str, crawlers: list[Any]) -> str:
    if _is_hex(identifier):
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

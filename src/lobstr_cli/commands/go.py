from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional
import typer

from lobstr_cli.display import (
    print_json, print_success, print_info, print_error,
    make_progress, print_detail,
)

go_app = typer.Typer()


def _find_squid_by_name(client, name: str, crawler_id: str):
    """Find an existing squid by name and crawler."""
    items = client.squids.list(name=name)
    for s in items:
        if s.name == name and s.crawler == crawler_id:
            return s
    return None


@go_app.command("go")
def go(
    crawler: str = typer.Argument(..., help="Crawler name or hash"),
    inputs: Optional[list[str]] = typer.Argument(None, help="URLs or keywords for tasks"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File with inputs (one per line)"),
    key: Optional[str] = typer.Option(
        None, "--key", "-k",
        help="Task param name (url, keyword, etc.). Defaults to the crawler's own "
        "declared task param when it declares exactly one, or `url` when it "
        "declares several including `url` or none at all; otherwise `go` "
        "refuses to guess and lists the choices. An explicit --key always wins.",
    ),
    param: Optional[list[str]] = typer.Option(None, "--param", "-p", help="KEY=VALUE, repeatable"),
    function: Optional[list[str]] = typer.Option(
        None, "--function", help="Add-on to turn on (NAME) or off (NAME=false), repeatable"
    ),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    output: str = typer.Option("results.csv", "--output", "-o", help="Output file path"),
    no_download: bool = typer.Option(False, "--no-download", help="Start run without waiting"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom squid name"),
    delete: bool = typer.Option(False, "--delete", help="Delete squid after completion"),
    empty: bool = typer.Option(False, "--empty", help="Empty old tasks before adding new ones (when reusing squid)"),
    account: Optional[list[str]] = typer.Option(
        None, "--account", "-a",
        help="Account username or hash to link (repeatable), for crawlers that need one. "
        "Auto-picked when the crawler needs an account, exactly one healthy account of the "
        "right type exists, and the squid has none attached yet; otherwise required — you'll "
        "get a list of candidates to choose from. Merged into whatever the squid already has, "
        "never silently replaced; a squid that already has accounts is left alone unless you "
        "pass --account explicitly.",
    ),
):
    """Full workflow: create squid, add tasks, run, download."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()

    from lobstr_cli.resolve import (
        resolve_crawler_id, parse_params, parse_functions, merge_params, resolve_accounts_with_type_check,
        healthy_account_candidates, default_task_key,
    )

    # 1. Resolve crawler
    print_info("Resolving crawler...")
    crawler_id = resolve_crawler_id(client, crawler)
    crawler_obj = client.crawlers.get(crawler_id)
    crawler_name = crawler_obj.name
    print_info(f"Using crawler: {crawler_name}")

    # A crawler that needs an account (`account: true`) but whose account
    # type slug the API/SDK couldn't parse (`account_type` falsy) must fail
    # loudly here, before anything is created. Silently falling through to
    # "no account needed" is exactly the bug this feature fixes (card
    # #HuwPdi7D): a squid would be created, made ready, and its run would die
    # with `no_accounts` — quietly, with no chance for --account to help,
    # since there is no type to validate a hash against.
    if crawler_obj.account and not crawler_obj.account_type:
        print_error(
            f"{crawler_name} needs an account, but the API didn't return a usable "
            "account type for it, so an account can't be matched or auto-picked "
            "safely. This looks like a bug in the crawler or the API response — "
            "please report it instead of running without an account."
        )
        raise typer.Exit(1)

    # Validate any explicit --account against the crawler's account type before
    # creating anything (a wrong-type or account-not-needed --account should
    # never get as far as an orphaned squid). Empty when --account wasn't
    # passed, whether or not the crawler needs an account.
    account_hashes = resolve_accounts_with_type_check(client, crawler_obj, account or [])

    # 2. Gather inputs
    task_inputs = list(inputs) if inputs else []
    if file:
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    task_inputs.append(line)
    if not task_inputs:
        print_error("No inputs provided. Pass URLs/keywords as arguments or use --file.")
        raise typer.Exit(1)

    user_params = parse_params(param) if param else {}

    squid_id = None
    run_id = None
    created_new_squid = False
    squid_params_meta = None

    # Default `--key` from the crawler's own declared task params, rather
    # than hardcoding `url` (card #Oy4yNR7I): a crawler like
    # `1stdibs-iter-categories` whose task input is `department` used to
    # fail every time with `[400] Invalid param: url`, after already
    # creating (and then deleting) a squid for nothing. Resolved once here,
    # before anything is created, so an unresolvable case (several params,
    # none of them `url`) fails loudly with no side effects — same principle
    # as the squid-param and account checks below. An explicit `--key`
    # always wins and skips this fetch entirely.
    if key is None:
        squid_params_meta = client.crawlers.params(crawler_id)
        key = default_task_key(crawler_name, squid_params_meta.task_params)

    if function:
        if squid_params_meta is None:
            squid_params_meta = client.crawlers.params(crawler_id)
        user_params["functions"] = parse_functions(function, squid_params_meta.functions or {})

    try:
        # 3. Find existing or create squid
        existing = _find_squid_by_name(client, name, crawler_id) if name else None
        if existing:
            squid_id = existing.id
            print_info(f"Reusing squid: {existing.name} ({squid_id[:12]})")
            if empty:
                client.squids.empty(squid_id, type="url")
                print_info("Emptied old tasks")
        else:
            # Fetch the crawler's squid-level params before creating
            # anything. A required squid param sent as null raises
            # ParamsNeeded from the API (apiviews.py ~l.5608), so a missing
            # required value must fail here, before an orphaned squid is
            # created — not surface later as a confusing error from
            # squids.update() or runs.start(). Already fetched above when
            # `--key` wasn't given; reuse it instead of asking the API twice.
            if squid_params_meta is None:
                squid_params_meta = client.crawlers.params(crawler_id)
            missing_required = sorted(
                k for k, v in squid_params_meta.squid_params.items()
                if k != "account" and isinstance(v, dict) and v.get("required")
                and user_params.get(k) is None
            )
            if missing_required:
                print_error(
                    f"{crawler_name} requires squid param(s): {', '.join(missing_required)}. "
                    "Pass them with --param KEY=VALUE."
                )
                raise typer.Exit(1)

            print_info(f"Creating squid ({len(task_inputs)} tasks)...")
            squid_obj = client.squids.create(crawler_id, name=name)
            squid_id = squid_obj.id
            created_new_squid = True
            print_info(f"Squid: {squid_obj.name} ({squid_id[:12]})")

        # 3.5 Link an account, for crawlers that need one. A squid that
        # already has account(s) attached — a reused squid, typically — is
        # never auto-picked into: that would silently add contention on an
        # account the user deliberately set up elsewhere. attach_accounts()
        # merges either way, so an explicit --account is always safe to send.
        if crawler_obj.account_type:
            current_accounts = (
                squid_obj.accounts if created_new_squid else client.squids.get(squid_id).accounts
            )
            if not account_hashes and not current_accounts:
                candidates = healthy_account_candidates(client, crawler_obj)
                if len(candidates) == 1:
                    picked = candidates[0]
                    account_hashes = [picked.id]
                    print_info(f"Auto-picked account: {picked.username} ({picked.id[:12]})")
                elif len(candidates) == 0:
                    print_error(
                        f"{crawler_name} needs a {crawler_obj.account_type} account and none of "
                        "yours is healthy and unlocked. Connect one with "
                        f"`lobstr accounts sync {crawler_obj.account_type} ...`, or pass --account."
                    )
                    raise typer.Exit(1)
                else:
                    names = ", ".join(f"{a.username} ({a.id[:12]})" for a in candidates[:10])
                    print_error(
                        f"Multiple healthy {crawler_obj.account_type} accounts available: "
                        f"{names}. Pick one with --account <username-or-hash>."
                    )
                    raise typer.Exit(1)
            elif not account_hashes and current_accounts:
                print_info(
                    f"Squid already has {len(current_accounts)} account(s) attached; leaving as is."
                )
            if account_hashes:
                client.squids.attach_accounts(squid_id, account_hashes)
                print_info(f"Linked account(s): {', '.join(h[:12] for h in account_hashes)}")

        # 4. Update squid params if needed
        update_kwargs: dict = {}
        if concurrency is not None:
            update_kwargs["concurrency"] = concurrency

        # A freshly created squid starts with is_ready=false server-side.
        # `POST /squids/{hash}` only flips it when the update actually
        # persists a field (`UpdateDeleteClustersView.update()` only calls
        # `cluster.save()` when it built a non-empty `json_data`); an empty
        # body `{}`, or `{"params": {}}`, or `--concurrency` set to the
        # value the squid already has, are all no-ops and leave the squid
        # not ready, so `runs.start()` below then fails with SquidNotReady.
        # Send every *optional* squid-level param the crawler declares
        # (the user's value, or None for the ones they didn't set — the
        # API's own `params` handler treats a non-empty dict as a change
        # even when every value is None); required params always carry the
        # user's real value, checked above, never None. A crawler with no
        # squid-level params at all (e.g. httpbin-get-json) has nothing to
        # put there, so fall back to re-sending the squid's own name:
        # `update()` writes it to `json_data` unconditionally, and setting
        # it to its current value has no visible effect.
        if created_new_squid:
            squid_level_keys = list(squid_params_meta.squid_params.keys())
            if squid_level_keys:
                params_dict = {k: None for k in squid_level_keys}
                params_dict.update(user_params)
                update_kwargs["params"] = params_dict
            elif user_params:
                update_kwargs["params"] = user_params
            else:
                update_kwargs["name"] = squid_obj.name
        elif user_params:
            flat = {k: v for k, v in user_params.items() if k != "functions"}
            update_kwargs["params"] = merge_params(
                client.squids.get(squid_id).params, flat, user_params.get("functions") or {}
            )

        # A reused squid (found by --name) is already ready, so only touch
        # it when the user asked to change something.
        if update_kwargs:
            client.squids.update(squid_id, **update_kwargs)

        # 5. Add tasks
        tasks = [{key: val} for val in task_inputs]
        result = client.tasks.add(squid=squid_id, tasks=tasks)
        print_info(f"Added {len(result.tasks)} tasks ({result.duplicated_count} duplicates)")

        # 6. Start run
        run = client.runs.start(squid=squid_id)
        run_id = run.id
        print_info(f"Run started: {run_id}")

        if no_download:
            if _state.get("json"):
                print_json({"squid": squid_id, "run": run_id})
            else:
                print_success(f"Run started. Watch with: lobstr run watch {run_id}")
            return

        # 7. Poll with progress
        with make_progress() as progress:
            ptask = progress.add_task("Running...", total=100)
            while True:
                stats = client.runs.stats(run_id)
                pct_str = stats.percent_done.replace("%", "")
                try:
                    pct = float(pct_str)
                except ValueError:
                    pct = 0
                progress.update(ptask, completed=pct, total=100,
                              description=f"Running... {stats.total_tasks_done}/{stats.total_tasks} tasks  ETA: {stats.eta or '?'}")
                if stats.is_done:
                    break
                time.sleep(3)

        # 8. Download (with retry — export may take a moment)
        final = client.runs.get(run_id)
        if _state.get("json"):
            print_json(asdict(final))
        else:
            downloaded = False
            for attempt in range(5):
                try:
                    client.runs.download(run_id, output)
                    downloaded = True
                    break
                except Exception:
                    pass
                if attempt == 0:
                    print_info("Waiting for export...")
                time.sleep(5)

            if downloaded:
                print_success(f"Downloaded {final.total_results} results to {output}")
            else:
                print_info("Export not ready. Try: lobstr run download " + run_id)

            print_detail([
                ("Status", final.status),
                ("Results", final.total_results),
                ("Duration", final.duration),
                ("Credits", final.credit_used),
            ])

        # 9. Delete squid if requested
        if delete:
            client.squids.delete(squid_id)
            print_info(f"Deleted squid {squid_id[:12]}")

    except KeyboardInterrupt:
        # Same cleanup rule as the Exception branch below, and for the same
        # reason: a squid `go` just created, with no run started yet, must
        # not survive a failure to leave this command — Ctrl-C is a failure
        # like any other from the squid's point of view, not a reason to
        # special-case an orphan into existence.
        if created_new_squid and squid_id and not run_id:
            try:
                client.squids.delete(squid_id)
                print_info(f"Cleaned up squid {squid_id[:12]}")
                squid_id = None
            except Exception:
                print_info(f"Squid {squid_id[:12]} may need manual cleanup")
        msg = "\nInterrupted."
        if squid_id:
            msg += f" Squid: {squid_id[:12]}"
        if run_id:
            msg += f" Run: {run_id}"
        print_info(msg)
        raise typer.Exit(0)
    except Exception:
        if created_new_squid and squid_id and not run_id:
            # Clean up orphaned squid if error before run started
            try:
                client.squids.delete(squid_id)
                print_info(f"Cleaned up squid {squid_id[:12]}")
            except Exception:
                print_info(f"Squid {squid_id[:12]} may need manual cleanup")
        raise

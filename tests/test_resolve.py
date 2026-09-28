from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock
from lobstr_cli.resolve import (
    match_hash_prefix,
    match_slug,
    match_name,
    match_username,
    match_crawler_name,
    resolve_crawler,
    resolve_squid,
    resolve_account,
    resolve_accounts_with_type_check,
    healthy_account_candidates,
    parse_param_value,
    parse_params,
    parse_functions,
    merge_params,
    require_full_hash,
    default_task_key,
)
from lobstrio.models.account import Account


# --- match_hash_prefix ---

class TestMatchHashPrefix:
    def test_exact_match(self):
        items = [{"id": "abc123"}, {"id": "abc456"}, {"id": "def789"}]
        assert match_hash_prefix("abc123", items) == "abc123"

    def test_unique_prefix(self):
        items = [{"id": "abc123"}, {"id": "def456"}]
        assert match_hash_prefix("abc", items) == "abc123"

    def test_ambiguous_prefix(self):
        items = [{"id": "abc123"}, {"id": "abc456"}]
        with pytest.raises(SystemExit):
            match_hash_prefix("abc", items)

    def test_no_match(self):
        items = [{"id": "abc123"}]
        with pytest.raises(SystemExit):
            match_hash_prefix("xyz", items)

    def test_custom_key(self):
        items = [{"hash": "abc123"}, {"hash": "def456"}]
        assert match_hash_prefix("abc", items, key="hash") == "abc123"

    def test_empty_items(self):
        with pytest.raises(SystemExit):
            match_hash_prefix("abc", [])

    def test_single_char_prefix(self):
        items = [{"id": "abc123"}, {"id": "def456"}]
        assert match_hash_prefix("a", items) == "abc123"

    def test_full_hash_exact_among_prefixes(self):
        """Exact match should win even if it's a prefix of another."""
        items = [{"id": "abc"}, {"id": "abc123"}]
        assert match_hash_prefix("abc", items) == "abc"

    def test_many_ambiguous_shows_max_five(self, capsys):
        items = [{"id": f"abc{i:03d}"} for i in range(10)]
        with pytest.raises(SystemExit):
            match_hash_prefix("abc", items)


# --- match_slug ---

class TestMatchSlug:
    def test_exact_slug(self):
        items = [
            {"id": "s1", "slug": "google-maps-leads-scraper", "name": "Google Maps Leads Scraper"},
            {"id": "s2", "slug": "linkedin-profile-scraper", "name": "LinkedIn Profile Scraper"},
        ]
        assert match_slug("google-maps-leads-scraper", items) == "s1"

    def test_slug_prefix(self):
        items = [
            {"id": "s1", "slug": "google-maps-leads-scraper", "name": "Google Maps Leads Scraper"},
            {"id": "s2", "slug": "linkedin-profile-scraper", "name": "LinkedIn Profile Scraper"},
        ]
        assert match_slug("google-maps", items) == "s1"

    def test_ambiguous_slug(self):
        items = [
            {"id": "s1", "slug": "google-maps-leads", "name": "Google Maps Leads"},
            {"id": "s2", "slug": "google-maps-reviews", "name": "Google Maps Reviews"},
        ]
        with pytest.raises(SystemExit):
            match_slug("google-maps", items)

    def test_no_match(self):
        items = [{"id": "s1", "slug": "google-maps-leads", "name": "Google Maps Leads"}]
        with pytest.raises(SystemExit):
            match_slug("facebook-ads", items)

    def test_empty_list(self):
        with pytest.raises(SystemExit):
            match_slug("anything", [])

    def test_exact_wins_over_prefix(self):
        items = [
            {"id": "s1", "slug": "google-maps", "name": "Google Maps"},
            {"id": "s2", "slug": "google-maps-leads-scraper", "name": "Google Maps Leads Scraper"},
        ]
        assert match_slug("google-maps", items) == "s1"

    def test_case_insensitive(self):
        items = [{"id": "s1", "slug": "google-maps-leads", "name": "Google Maps Leads"}]
        assert match_slug("Google-Maps-Leads", items) == "s1"


# --- match_name ---

class TestMatchName:
    def test_exact_match(self):
        items = [{"id": "s1", "name": "My Leads"}, {"id": "s2", "name": "My Reviews"}]
        assert match_name("My Leads", items) == "s1"

    def test_case_insensitive(self):
        items = [{"id": "s1", "name": "My Leads Scraper"}]
        assert match_name("my leads scraper", items) == "s1"

    def test_substring_match(self):
        items = [{"id": "s1", "name": "Google Maps Leads"}, {"id": "s2", "name": "LinkedIn Profiles"}]
        assert match_name("maps leads", items) == "s1"

    def test_ambiguous_name(self):
        items = [{"id": "s1", "name": "Maps Leads"}, {"id": "s2", "name": "Maps Reviews"}]
        with pytest.raises(SystemExit):
            match_name("Maps", items)

    def test_no_match(self):
        items = [{"id": "s1", "name": "My Leads"}]
        with pytest.raises(SystemExit):
            match_name("facebook", items)

    def test_empty_list(self):
        with pytest.raises(SystemExit):
            match_name("anything", [])

    def test_exact_wins_over_substring(self):
        items = [{"id": "s1", "name": "Maps"}, {"id": "s2", "name": "Google Maps Leads"}]
        assert match_name("Maps", items) == "s1"


# --- resolve_squid ---

class TestResolveSquid:
    def _mock_client(self, squids):
        mock = MagicMock()
        mock.squids.iter.return_value = squids
        return mock

    def test_resolve_by_hash_prefix(self):
        client = self._mock_client([{"id": "abc123def456", "name": "My Scraper"}])
        assert resolve_squid(client, "abc123") == "abc123def456"

    def test_resolve_by_exact_name(self):
        client = self._mock_client([
            {"id": "s1", "name": "Maps"},
            {"id": "s2", "name": "Google Maps Leads"},
        ])
        assert resolve_squid(client, "Maps") == "s1"

    def test_resolve_by_name_substring(self):
        client = self._mock_client([{"id": "s1", "name": "My Leads Scraper"}])
        assert resolve_squid(client, "My Leads") == "s1"

    def test_resolve_name_case_insensitive(self):
        client = self._mock_client([{"id": "s1", "name": "My Leads"}])
        assert resolve_squid(client, "my leads") == "s1"

    def test_resolve_alias(self):
        client = self._mock_client([{"id": "abc123def456", "name": "Scraper"}])
        from unittest.mock import patch
        with patch("lobstr_cli.config.resolve_alias", return_value="abc123def456"):
            assert resolve_squid(client, "@maps") == "abc123def456"

    def test_hash_first_priority(self):
        """Pure hex input should try hash before name."""
        client = self._mock_client([{"id": "deadbeef1234", "name": "Other"}])
        assert resolve_squid(client, "deadbeef") == "deadbeef1234"

    def test_no_match_raises(self):
        client = self._mock_client([{"id": "abc123", "name": "My Scraper"}])
        with pytest.raises(SystemExit):
            resolve_squid(client, "nonexistent")

    def test_ambiguous_name_raises(self):
        client = self._mock_client([
            {"id": "s1", "name": "Google Maps Leads"},
            {"id": "s2", "name": "Google Maps Reviews"},
        ])
        with pytest.raises(SystemExit):
            resolve_squid(client, "Google Maps")


# --- match_crawler_name ---

class TestMatchCrawlerName:
    def test_exact_match(self):
        crawlers = [
            {"id": "c1", "name": "LinkedIn Profile Scraper"},
            {"id": "c2", "name": "Google Maps Reviews"},
        ]
        assert match_crawler_name("LinkedIn Profile Scraper", crawlers) == "c1"

    def test_case_insensitive_exact(self):
        crawlers = [{"id": "c1", "name": "Google Maps Leads Scraper"}]
        assert match_crawler_name("google maps leads scraper", crawlers) == "c1"

    def test_substring_match(self):
        crawlers = [
            {"id": "c1", "name": "LinkedIn Profile Scraper"},
            {"id": "c2", "name": "Google Maps Reviews"},
        ]
        assert match_crawler_name("linkedin profile", crawlers) == "c1"

    def test_ambiguous_name(self):
        crawlers = [
            {"id": "c1", "name": "LinkedIn Profile Scraper"},
            {"id": "c2", "name": "LinkedIn Company Scraper"},
        ]
        with pytest.raises(SystemExit):
            match_crawler_name("linkedin", crawlers)

    def test_no_match(self):
        crawlers = [{"id": "c1", "name": "LinkedIn Profile Scraper"}]
        with pytest.raises(SystemExit):
            match_crawler_name("facebook", crawlers)

    def test_empty_list(self):
        with pytest.raises(SystemExit):
            match_crawler_name("anything", [])

    def test_partial_word_match(self):
        crawlers = [
            {"id": "c1", "name": "Google Maps Leads Scraper"},
            {"id": "c2", "name": "Google Maps Reviews Scraper"},
        ]
        assert match_crawler_name("Maps Leads", crawlers) == "c1"


# --- resolve_crawler ---

class TestResolveCrawler:
    def test_resolve_by_hash(self):
        crawlers = [
            {"id": "abc123def456", "name": "Some Crawler", "slug": "some-crawler"},
            {"id": "def789abc012", "name": "Other Crawler", "slug": "other-crawler"},
        ]
        assert resolve_crawler("abc123", crawlers) == "abc123def456"

    def test_resolve_by_slug(self):
        crawlers = [{"id": "c1", "name": "Google Maps Leads Scraper", "slug": "google-maps-leads-scraper"}]
        assert resolve_crawler("google-maps-leads-scraper", crawlers) == "c1"

    def test_resolve_by_slug_prefix(self):
        crawlers = [
            {"id": "c1", "name": "Google Maps Leads Scraper", "slug": "google-maps-leads-scraper"},
            {"id": "c2", "name": "LinkedIn Profile Scraper", "slug": "linkedin-profile-scraper"},
        ]
        assert resolve_crawler("google-maps", crawlers) == "c1"

    def test_resolve_by_name(self):
        crawlers = [{"id": "abc123def456", "name": "Google Maps Leads Scraper", "slug": "google-maps-leads-scraper"}]
        assert resolve_crawler("Google Maps", crawlers) == "abc123def456"

    def test_hash_fallback_to_name(self):
        crawlers = [{"id": "abc123", "name": "My Scraper", "slug": "my-scraper"}]
        assert resolve_crawler("My Scraper", crawlers) == "abc123"

    def test_hex_like_tries_hash_first(self):
        crawlers = [{"id": "xyz789", "name": "deadbeef", "slug": "deadbeef"}]
        assert resolve_crawler("deadbeef", crawlers) == "xyz789"

    def test_resolve_full_hash(self):
        crawlers = [{"id": "abc123def456789012345678", "name": "Crawler", "slug": "crawler"}]
        assert resolve_crawler("abc123def456789012345678", crawlers) == "abc123def456789012345678"


# --- parse_param_value ---

class TestParseParamValue:
    def test_integer(self):
        assert parse_param_value("42") == 42

    def test_negative_integer(self):
        assert parse_param_value("-5") == -5

    def test_float(self):
        assert parse_param_value("3.14") == 3.14

    def test_true(self):
        assert parse_param_value("true") is True

    def test_false(self):
        assert parse_param_value("false") is False

    def test_true_uppercase(self):
        assert parse_param_value("True") is True

    def test_false_mixed_case(self):
        assert parse_param_value("FALSE") is False

    def test_none(self):
        assert parse_param_value("none") is None

    def test_none_uppercase(self):
        assert parse_param_value("None") is None

    def test_string(self):
        assert parse_param_value("hello world") == "hello world"

    def test_empty_string(self):
        assert parse_param_value("") == ""

    def test_string_with_numbers(self):
        assert parse_param_value("abc123") == "abc123"

    def test_zero(self):
        assert parse_param_value("0") == 0

    def test_float_zero(self):
        assert parse_param_value("0.0") == 0.0


# --- parse_params ---

class TestParseParams:
    def test_single_param(self):
        assert parse_params(["max_results=50"]) == {"max_results": 50}

    def test_multiple_params(self):
        result = parse_params(["max_results=50", "language=English", "geo_match=true"])
        assert result == {"max_results": 50, "language": "English", "geo_match": True}

    def test_param_with_equals_in_value(self):
        result = parse_params(["url=https://example.com?a=1"])
        assert result == {"url": "https://example.com?a=1"}

    def test_empty_value(self):
        result = parse_params(["key="])
        assert result == {"key": ""}

    def test_none_value(self):
        result = parse_params(["key=none"])
        assert result == {"key": None}

    def test_empty_list(self):
        assert parse_params([]) == {}

    def test_overwrite_duplicate_key(self):
        result = parse_params(["key=first", "key=second"])
        assert result == {"key": "second"}


# --- parse_functions ---

class TestParseFunctions:
    KNOWN = {"get_videos": {}, "get_shorts": {}}

    def test_name_turns_on(self):
        assert parse_functions(["get_videos"], self.KNOWN) == {"get_videos": True}

    def test_name_false_turns_off(self):
        assert parse_functions(["get_videos", "get_shorts=false"], self.KNOWN) == {"get_videos": True, "get_shorts": False}

    def test_unknown_name_exits(self):
        with pytest.raises(SystemExit):
            parse_functions(["get_reels"], self.KNOWN)


# --- merge_params ---

class TestMergeParams:
    SAVED = {"language": "English", "max_results": 200, "functions": {"a": False, "b": True}}

    def test_keeps_saved_and_applies_change(self):
        merged = merge_params(self.SAVED, {"max_results": 5}, {})
        assert merged == {"language": "English", "max_results": 5, "functions": {"a": False, "b": True}}

    def test_functions_merge_with_saved(self):
        assert merge_params(self.SAVED, {}, {"a": True})["functions"] == {"a": True, "b": True}

    def test_no_saved_params(self):
        assert merge_params(None, {"x": 1}, {"a": True}) == {"x": 1, "functions": {"a": True}}


# --- require_full_hash ---

class TestRequireFullHash:
    def test_valid_32_char_hash(self):
        # Should not raise
        require_full_hash("a" * 32, "run")

    def test_short_hash_raises(self):
        with pytest.raises(SystemExit):
            require_full_hash("abc123def456", "run")

    def test_12_char_hash_raises(self):
        with pytest.raises(SystemExit):
            require_full_hash("26a4377e8b37", "task")

    def test_empty_hash_raises(self):
        with pytest.raises(SystemExit):
            require_full_hash("", "run")

    def test_31_char_hash_raises(self):
        with pytest.raises(SystemExit):
            require_full_hash("a" * 31, "run")

    def test_longer_than_32_passes(self):
        # Should not raise for >= 32
        require_full_hash("a" * 40, "run")


# --- match_username ---

class TestMatchUsername:
    def test_exact_match(self):
        items = [{"id": "a1", "username": "johndoe"}, {"id": "a2", "username": "janedoe"}]
        assert match_username("johndoe", items) == "a1"

    def test_case_insensitive(self):
        items = [{"id": "a1", "username": "JohnDoe"}]
        assert match_username("johndoe", items) == "a1"

    def test_substring_match(self):
        items = [{"id": "a1", "username": "john_twitter"}, {"id": "a2", "username": "jane_facebook"}]
        assert match_username("twitter", items) == "a1"

    def test_no_match(self):
        items = [{"id": "a1", "username": "johndoe"}]
        with pytest.raises(SystemExit):
            match_username("notfound", items)

    def test_ambiguous_match(self):
        items = [{"id": "a1", "username": "john_twitter"}, {"id": "a2", "username": "john_facebook"}]
        with pytest.raises(SystemExit):
            match_username("john", items)

    def test_exact_wins_over_substring(self):
        items = [
            {"id": "a1", "username": "john"},
            {"id": "a2", "username": "john_doe"},
        ]
        assert match_username("john", items) == "a1"


# --- resolve_account ---

class TestResolveAccount:
    def test_resolve_by_hash_prefix(self):
        client = MagicMock()
        client.accounts.iter.return_value = [{"id": "aabb11cc22dd", "username": "johndoe"}]
        assert resolve_account(client, "aabb11") == "aabb11cc22dd"

    def test_resolve_by_username(self):
        client = MagicMock()
        client.accounts.iter.return_value = [{"id": "acc123", "username": "johndoe"}]
        assert resolve_account(client, "johndoe") == "acc123"

    def test_hex_falls_back_to_username(self):
        client = MagicMock()
        client.accounts.iter.return_value = [{"id": "xyz789", "username": "deadbeef"}]
        assert resolve_account(client, "deadbeef") == "xyz789"

    def test_hex_prefers_hash_over_username(self):
        client = MagicMock()
        client.accounts.iter.return_value = [{"id": "deadbeef1234", "username": "deadbeef"}]
        assert resolve_account(client, "deadbeef") == "deadbeef1234"


# --- pagination: list() returns one page, so resolution must use iter() ---


class TestResolvePaginates:
    def test_resolve_squid_looks_past_first_page(self):
        mock = MagicMock()
        mock.squids.list.return_value = [{"id": "aaa111", "name": "Page One"}]
        mock.squids.iter.return_value = [
            {"id": "aaa111", "name": "Page One"},
            {"id": "bbb222", "name": "Page Two"},
        ]
        assert resolve_squid(mock, "Page Two") == "bbb222"
        mock.squids.list.assert_not_called()

    def test_resolve_account_looks_past_first_page(self):
        mock = MagicMock()
        mock.accounts.list.return_value = [{"id": "aaa111", "username": "first@x.com"}]
        mock.accounts.iter.return_value = [
            {"id": "aaa111", "username": "first@x.com"},
            {"id": "bbb222", "username": "second@x.com"},
        ]
        assert resolve_account(mock, "second@x.com") == "bbb222"
        mock.accounts.list.assert_not_called()


# --- resolve_accounts_with_type_check ---

def _crawler(name="Sales Nav Scraper", account_type="sales-nav-sync"):
    return SimpleNamespace(name=name, account_type=account_type)


class TestResolveAccountsWithTypeCheck:
    def test_empty_identifiers_is_a_noop_even_without_account_type(self):
        client = MagicMock()
        assert resolve_accounts_with_type_check(client, _crawler(account_type=None), []) == []
        client.accounts.iter.assert_not_called()

    def test_crawler_without_account_type_rejects_explicit_account(self):
        client = MagicMock()
        with pytest.raises(SystemExit):
            resolve_accounts_with_type_check(client, _crawler(account_type=None), ["someone"])

    def test_resolves_matching_type(self):
        client = MagicMock()
        client.accounts.iter.return_value = [
            {"id": "ac1", "username": "jane", "type": "sales-nav-sync"},
        ]
        assert resolve_accounts_with_type_check(client, _crawler(), ["jane"]) == ["ac1"]

    def test_wrong_type_fails_with_both_types_named(self):
        client = MagicMock()
        client.accounts.iter.return_value = [
            {"id": "ac1", "username": "jane", "type": "linkedin-sync"},
        ]
        with pytest.raises(SystemExit):
            resolve_accounts_with_type_check(client, _crawler(), ["jane"])

    def test_unknown_account_fails_before_any_type_check(self):
        client = MagicMock()
        client.accounts.iter.return_value = [
            {"id": "ac1", "username": "jane", "type": "sales-nav-sync"},
        ]
        with pytest.raises(SystemExit):
            resolve_accounts_with_type_check(client, _crawler(), ["nobody"])

    def test_fetches_the_account_list_exactly_once_for_several_identifiers(self):
        """Regression: resolving used to call resolve_account() per identifier,
        each doing its own client.accounts.iter() — a second listing that
        disagreed with the first could return a hash absent from the first
        snapshot, silently skipping the type check."""
        client = MagicMock()
        client.accounts.iter.return_value = [
            {"id": "ac1", "username": "jane", "type": "sales-nav-sync"},
            {"id": "ac2", "username": "john", "type": "sales-nav-sync"},
        ]
        result = resolve_accounts_with_type_check(client, _crawler(), ["jane", "john"])
        assert result == ["ac1", "ac2"]
        assert client.accounts.iter.call_count == 1

    def test_type_check_is_never_skipped_for_a_resolved_hash(self):
        """Every hash resolve_accounts_with_type_check returns comes from the
        one snapshot it fetched, so the type check below can never see
        `account is None` and silently let a wrong-type hash through."""
        client = MagicMock()
        client.accounts.iter.return_value = [
            {"id": "ac1", "username": "jane", "type": "linkedin-sync"},
        ]
        with pytest.raises(SystemExit):
            resolve_accounts_with_type_check(client, _crawler(), ["ac1"])


# --- healthy_account_candidates ---

def _acct(id, type="sales-nav-sync", status="200", status_code_info="ok", resets_in=None):
    return Account(
        id=id, username=f"user-{id}", type=type, status_code_info=status_code_info,
        status_code_description=None, baseurl=None, created_at=None, updated_at=None,
        last_synchronization_time=None, squids=[], params={},
        status=status, resets_in=resets_in,
    )


class TestHealthyAccountCandidates:
    def test_matches_the_worker_condition(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1")]
        assert [a.id for a in healthy_account_candidates(client, _crawler())] == ["ac1"]

    def test_excludes_wrong_type(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1", type="linkedin-sync")]
        assert healthy_account_candidates(client, _crawler()) == []

    def test_excludes_non_200_status(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1", status="429")]
        assert healthy_account_candidates(client, _crawler()) == []

    def test_excludes_cookies_expired(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1", status_code_info="cookies_expired")]
        assert healthy_account_candidates(client, _crawler()) == []

    def test_excludes_locked(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1", resets_in=42)]
        assert healthy_account_candidates(client, _crawler()) == []

    def test_includes_account_with_expired_lock(self):
        client = MagicMock()
        client.accounts.iter.return_value = [_acct("ac1", resets_in=0)]
        assert [a.id for a in healthy_account_candidates(client, _crawler())] == ["ac1"]


# --- default_task_key (card #Oy4yNR7I) ---

class TestDefaultTaskKey:
    def test_single_declared_param(self):
        # 1stdibs-iter-categories: one task param, `department`.
        task_params = {"department": {"type": "string", "required": False}}
        assert default_task_key("1stdibs Iter Categories", task_params) == "department"

    def test_single_declared_param_ignores_bare_max_int(self):
        # A crawler with `max_tasks` set carries `task["max"]` as a bare int,
        # not a declared field; it must not count as a second param.
        task_params = {"department": {"type": "string", "required": False}, "max": 1}
        assert default_task_key("Some Crawler", task_params) == "department"

    def test_no_declared_params_falls_back_to_url(self):
        assert default_task_key("Christies PM Iter Auctions", {}) == "url"

    def test_several_declared_params_keeps_url_when_present(self):
        task_params = {
            "url": {"type": "string", "required": True},
            "department": {"type": "string", "required": False},
        }
        assert default_task_key("Artcurial Iter Results", task_params) == "url"

    def test_several_declared_params_without_url_raises(self):
        task_params = {
            "asin": {"type": "string", "required": True},
            "marketplace": {"type": "string", "required": False},
        }
        with pytest.raises(SystemExit):
            default_task_key("Amazon Asin Collector", task_params)

    def test_several_declared_params_without_url_names_the_choices(self, capsys):
        task_params = {
            "asin": {"type": "string", "required": True},
            "marketplace": {"type": "string", "required": False},
        }
        with pytest.raises(SystemExit):
            default_task_key("Amazon Asin Collector", task_params)
        out = capsys.readouterr()
        assert "asin" in (out.out + out.err)
        assert "marketplace" in (out.out + out.err)

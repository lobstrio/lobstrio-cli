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
    parse_param_value,
    parse_params,
    require_full_hash,
)


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
        mock.squids.list.return_value = squids
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
        client.accounts.list.return_value = [{"id": "aabb11cc22dd", "username": "johndoe"}]
        assert resolve_account(client, "aabb11") == "aabb11cc22dd"

    def test_resolve_by_username(self):
        client = MagicMock()
        client.accounts.list.return_value = [{"id": "acc123", "username": "johndoe"}]
        assert resolve_account(client, "johndoe") == "acc123"

    def test_hex_falls_back_to_username(self):
        client = MagicMock()
        client.accounts.list.return_value = [{"id": "xyz789", "username": "deadbeef"}]
        assert resolve_account(client, "deadbeef") == "xyz789"

    def test_hex_prefers_hash_over_username(self):
        client = MagicMock()
        client.accounts.list.return_value = [{"id": "deadbeef1234", "username": "deadbeef"}]
        assert resolve_account(client, "deadbeef") == "deadbeef1234"

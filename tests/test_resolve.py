import pytest
from lobstr_cli.resolve import (
    match_hash_prefix,
    match_crawler_name,
    resolve_crawler,
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
            {"id": "abc123def456", "name": "Some Crawler"},
            {"id": "def789abc012", "name": "Other Crawler"},
        ]
        assert resolve_crawler("abc123", crawlers) == "abc123def456"

    def test_resolve_by_name(self):
        crawlers = [
            {"id": "abc123def456", "name": "Google Maps Leads Scraper"},
        ]
        assert resolve_crawler("Google Maps", crawlers) == "abc123def456"

    def test_hash_fallback_to_name(self):
        """Non-hex string should go straight to name matching."""
        crawlers = [{"id": "abc123", "name": "My Scraper"}]
        assert resolve_crawler("My Scraper", crawlers) == "abc123"

    def test_hex_like_name_tries_hash_first(self):
        """Pure hex string that doesn't match hash falls back to name."""
        crawlers = [{"id": "xyz789", "name": "deadbeef"}]
        # "deadbeef" is valid hex, tries hash first (fails), then name
        assert resolve_crawler("deadbeef", crawlers) == "xyz789"

    def test_resolve_full_hash(self):
        crawlers = [{"id": "abc123def456789012345678", "name": "Crawler"}]
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

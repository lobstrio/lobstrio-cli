import pytest
from lobstr_cli.resolve import match_hash_prefix, match_crawler_name


def test_match_hash_prefix_exact():
    items = [{"id": "abc123"}, {"id": "abc456"}, {"id": "def789"}]
    assert match_hash_prefix("abc123", items) == "abc123"


def test_match_hash_prefix_unique():
    items = [{"id": "abc123"}, {"id": "def456"}]
    assert match_hash_prefix("abc", items) == "abc123"


def test_match_hash_prefix_ambiguous():
    items = [{"id": "abc123"}, {"id": "abc456"}]
    with pytest.raises(SystemExit):
        match_hash_prefix("abc", items)


def test_match_hash_prefix_no_match():
    items = [{"id": "abc123"}]
    with pytest.raises(SystemExit):
        match_hash_prefix("xyz", items)


def test_match_crawler_name_exact():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "Google Maps Reviews"},
    ]
    assert match_crawler_name("LinkedIn Profile Scraper", crawlers) == "c1"


def test_match_crawler_name_substring():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "Google Maps Reviews"},
    ]
    assert match_crawler_name("linkedin profile", crawlers) == "c1"


def test_match_crawler_name_ambiguous():
    crawlers = [
        {"id": "c1", "name": "LinkedIn Profile Scraper"},
        {"id": "c2", "name": "LinkedIn Company Scraper"},
    ]
    with pytest.raises(SystemExit):
        match_crawler_name("linkedin", crawlers)


def test_match_crawler_name_no_match():
    crawlers = [{"id": "c1", "name": "LinkedIn Profile Scraper"}]
    with pytest.raises(SystemExit):
        match_crawler_name("facebook", crawlers)

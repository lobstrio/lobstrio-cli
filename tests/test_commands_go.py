import pytest
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

CRAWLERS = {
    "data": [
        {"id": "crawler1abc", "name": "Google Maps Leads Scraper"},
    ]
}


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(squids_by_name=None):
    """Create a mock client for go command tests."""
    mock = MagicMock()

    def get_side_effect(path, **kw):
        if path == "/crawlers":
            return CRAWLERS
        if path == "/squids":
            if squids_by_name:
                return {"data": squids_by_name}
            return {"data": []}
        if "/stats" in path:
            return {
                "total_tasks": 1, "total_tasks_done": 1,
                "is_done": True, "percent_done": "100%", "eta": "0s",
            }
        if "/download" in path:
            return {"s3": "https://s3.example.com/results.csv"}
        if path.startswith("/runs/"):
            return {
                "id": "run123", "status": "finished",
                "total_results": 10, "duration": 30, "credit_used": 5,
            }
        return {}

    mock.get.side_effect = get_side_effect

    def post_side_effect(path, **kw):
        if path == "/squids":
            return {"id": "newsquid123", "name": "Test Squid"}
        if path == "/tasks":
            tasks = kw.get("json", {}).get("tasks", [])
            return {"tasks": [{"id": f"t{i}"} for i in range(len(tasks))], "duplicated_count": 0}
        if path == "/runs":
            return {"id": "run123"}
        return {}

    mock.post.side_effect = post_side_effect
    mock.download.return_value = None
    mock.delete.return_value = {}
    return mock


class TestGoBasic:
    def test_go_full_workflow(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://maps.google.com/place1"])
        assert result.exit_code == 0
        assert "Downloaded" in result.output

    def test_go_multiple_inputs(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "https://b.com"])
        assert result.exit_code == 0

    def test_go_no_inputs_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps"])
        assert result.exit_code == 1


class TestGoKey:
    def test_custom_key(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "pizza", "--key", "keyword"])
        assert result.exit_code == 0
        # Verify tasks were created with keyword key
        post_calls = mock.post.call_args_list
        tasks_call = [c for c in post_calls if c[0][0] == "/tasks"][0]
        assert tasks_call[1]["json"]["tasks"] == [{"keyword": "pizza"}]


class TestGoFile:
    def test_file_input(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://a.com\nhttps://b.com\n# comment\n\n")
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "--file", str(f)])
        assert result.exit_code == 0
        post_calls = mock.post.call_args_list
        tasks_call = [c for c in post_calls if c[0][0] == "/tasks"][0]
        tasks = tasks_call[1]["json"]["tasks"]
        assert len(tasks) == 2  # comment and empty line filtered


class TestGoNoDownload:
    def test_no_download(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--no-download"])
        assert result.exit_code == 0
        mock.download.assert_not_called()


class TestGoDelete:
    def test_delete_after_completion(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--delete"])
        assert result.exit_code == 0
        # Verify squid was deleted
        delete_calls = mock.delete.call_args_list
        assert any("/squids/" in str(c) for c in delete_calls)


class TestGoReuse:
    def test_reuse_existing_squid(self):
        existing = [{"id": "existing123", "name": "MyScraper", "crawler": "crawler1abc"}]
        mock = _mock_client(squids_by_name=existing)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--name", "MyScraper"])
        assert result.exit_code == 0
        # Should NOT have created a new squid
        post_calls = mock.post.call_args_list
        squid_create = [c for c in post_calls if c[0][0] == "/squids" and len(c[0][0]) == len("/squids")]
        assert len(squid_create) == 0

    def test_reuse_with_empty(self):
        existing = [{"id": "existing123", "name": "MyScraper", "crawler": "crawler1abc"}]
        mock = _mock_client(squids_by_name=existing)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--name", "MyScraper", "--empty"])
        assert result.exit_code == 0
        # Verify empty was called
        post_calls = mock.post.call_args_list
        empty_calls = [c for c in post_calls if "/empty" in str(c)]
        assert len(empty_calls) == 1


class TestGoParams:
    def test_squid_params(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com",
                                         "--param", "max_results=200", "--param", "language=English"])
        assert result.exit_code == 0
        # Verify params were sent to squid update
        post_calls = mock.post.call_args_list
        update_calls = [c for c in post_calls if "/squids/" in str(c) and "/empty" not in str(c)]
        assert len(update_calls) >= 1

    def test_concurrency(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--concurrency", "3"])
        assert result.exit_code == 0


class TestGoCleanup:
    def test_cleanup_orphaned_squid_on_error(self):
        mock = _mock_client()
        # Make task creation fail
        original_post = mock.post.side_effect
        call_count = [0]

        def failing_post(path, **kw):
            call_count[0] += 1
            if path == "/tasks":
                raise Exception("Task creation failed")
            return original_post(path, **kw)

        mock.post.side_effect = failing_post
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code != 0
        # Verify cleanup was attempted
        delete_calls = mock.delete.call_args_list
        assert len(delete_calls) >= 1

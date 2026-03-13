import pytest
import json
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.squid import Squid


runner = CliRunner()

SQUIDS = [
    Squid(
        id="squid1abc123def456", name="My Squid", crawler="c1",
        crawler_name="Google Maps", is_active=True, is_ready=True,
        concurrency=1, to_complete=None, last_run_status=None,
        last_run_at=None, total_runs=0, export_unique_results=False,
        params={},
    ),
]

RESULTS = [
    {"id": "r1", "url": "https://a.com", "title": "Page A", "squid": "s1"},
    {"id": "r2", "url": "https://b.com", "title": "Page B", "squid": "s1"},
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(results=None):
    mock = MagicMock()
    mock.squids.list.return_value = SQUIDS
    mock.results.list.return_value = results if results is not None else RESULTS
    return mock


class TestResultsGet:
    def test_get_json_format(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid"])
        assert result.exit_code == 0
        assert "https://a.com" in result.output

    def test_get_csv_format(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_get_save_json(self, tmp_path):
        out_file = tmp_path / "out.json"
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert len(data) == 2

    def test_get_save_csv(self, tmp_path):
        out_file = tmp_path / "out.csv"
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv", "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "url" in content
        assert "https://a.com" in content

    def test_get_empty_results(self):
        mock = _mock_client(results=[])
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv"])
        assert result.exit_code == 0

    def test_get_with_pagination(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--page", "2", "--page-size", "10"])
        assert result.exit_code == 0
        mock.results.list.assert_called_once_with(squid="squid1abc123def456", page=2, page_size=10)

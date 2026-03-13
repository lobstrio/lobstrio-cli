import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.squid import Squid
from lobstrio.models.delivery import (
    EmailDelivery, GoogleSheetDelivery, S3Delivery,
    WebhookDelivery, WebhookEvents, SFTPDelivery,
)


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


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.squids.list.return_value = SQUIDS
    return mock


class TestDeliveryEmail:
    def test_configure_email(self):
        mock = _mock_client()
        mock.delivery.email.return_value = EmailDelivery(email="user@example.com", notifications=True)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "email", "My Squid", "--email", "user@example.com"])
        assert result.exit_code == 0
        mock.delivery.email.assert_called_once_with(
            "squid1abc123def456", email="user@example.com", notifications=True,
        )

    def test_configure_email_no_notifications(self):
        mock = _mock_client()
        mock.delivery.email.return_value = EmailDelivery(email="user@example.com", notifications=False)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "email", "My Squid", "--email", "user@example.com", "--no-notifications"])
        assert result.exit_code == 0
        mock.delivery.email.assert_called_once_with(
            "squid1abc123def456", email="user@example.com", notifications=False,
        )

    def test_email_json_mode(self):
        mock = _mock_client()
        mock.delivery.email.return_value = EmailDelivery(email="user@example.com", notifications=True)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "delivery", "email", "My Squid", "--email", "user@example.com"])
        assert result.exit_code == 0


class TestDeliveryGoogleSheet:
    def test_configure_googlesheet(self):
        mock = _mock_client()
        mock.delivery.google_sheet.return_value = GoogleSheetDelivery(
            url="https://docs.google.com/spreadsheets/d/123", append=False, is_active=True,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "googlesheet", "My Squid", "--url", "https://docs.google.com/spreadsheets/d/123"])
        assert result.exit_code == 0
        assert "configured" in result.output

    def test_configure_with_append(self):
        mock = _mock_client()
        mock.delivery.google_sheet.return_value = GoogleSheetDelivery(
            url="https://...", append=True, is_active=True,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "googlesheet", "My Squid", "--url", "https://...", "--append"])
        assert result.exit_code == 0
        mock.delivery.google_sheet.assert_called_once_with(
            "squid1abc123def456", url="https://...", append=True, is_active=True,
        )


class TestDeliveryS3:
    def test_configure_s3(self):
        mock = _mock_client()
        mock.delivery.s3.return_value = S3Delivery(bucket="mybucket", target_path="exports", is_active=True)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "s3", "My Squid", "--bucket", "mybucket", "--target-path", "exports"])
        assert result.exit_code == 0
        assert "configured" in result.output

    def test_s3_with_credentials(self):
        mock = _mock_client()
        mock.delivery.s3.return_value = S3Delivery(bucket="b", target_path="p", is_active=True)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "s3", "My Squid",
                "--bucket", "b", "--target-path", "p",
                "--aws-access-key", "AKIA...", "--aws-secret-key", "secret",
            ])
        assert result.exit_code == 0
        mock.delivery.s3.assert_called_once_with(
            "squid1abc123def456", bucket="b", target_path="p",
            aws_access_key="AKIA...", aws_secret_key="secret", is_active=True,
        )


class TestDeliveryWebhook:
    def test_configure_webhook(self):
        mock = _mock_client()
        mock.delivery.webhook.return_value = WebhookDelivery(
            url="https://hook.example.com", is_active=True, retry=True,
            events=WebhookEvents(run_running=False, run_paused=False, run_done=True, run_error=True),
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "webhook", "My Squid", "--url", "https://hook.example.com"])
        assert result.exit_code == 0
        assert "configured" in result.output
        mock.delivery.webhook.assert_called_once_with(
            "squid1abc123def456", url="https://hook.example.com",
            is_active=True, retry=True,
            on_running=False, on_paused=False, on_done=True, on_error=True,
        )


class TestDeliverySftp:
    def test_configure_sftp(self):
        mock = _mock_client()
        mock.delivery.sftp.return_value = SFTPDelivery(
            host="sftp.example.com", port=22, username="user",
            directory="/upload", is_active=True,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "sftp", "My Squid",
                "--host", "sftp.example.com",
                "--username", "user", "--password", "pass",
                "--directory", "/upload",
            ])
        assert result.exit_code == 0
        assert "configured" in result.output


class TestDeliveryTests:
    def test_test_email_pass(self):
        mock = _mock_client()
        mock.delivery.test_email.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-email", "--email", "user@example.com"])
        assert result.exit_code == 0
        assert "passed" in result.output

    def test_test_email_fail(self):
        mock = _mock_client()
        mock.delivery.test_email.return_value = {"success": False}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-email", "--email", "bad@example.com"])
        assert result.exit_code == 1

    def test_test_googlesheet(self):
        mock = _mock_client()
        mock.delivery.test_google_sheet.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-googlesheet", "--url", "https://docs.google.com/..."])
        assert result.exit_code == 0

    def test_test_s3(self):
        mock = _mock_client()
        mock.delivery.test_s3.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-s3", "--bucket", "mybucket"])
        assert result.exit_code == 0

    def test_test_webhook(self):
        mock = _mock_client()
        mock.delivery.test_webhook.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-webhook", "--url", "https://hook.example.com"])
        assert result.exit_code == 0

    def test_test_sftp(self):
        mock = _mock_client()
        mock.delivery.test_sftp.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "test-sftp",
                "--host", "sftp.example.com",
                "--username", "user", "--password", "pass",
                "--directory", "/upload",
            ])
        assert result.exit_code == 0

    def test_test_json_mode(self):
        mock = _mock_client()
        mock.delivery.test_email.return_value = {"success": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "delivery", "test-email", "--email", "user@example.com"])
        assert result.exit_code == 0

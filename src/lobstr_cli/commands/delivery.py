from __future__ import annotations

from dataclasses import asdict
from typing import Optional
import typer

from lobstr_cli.display import print_json, print_detail, print_success, print_error
from lobstr_cli.resolve import resolve_squid as _resolve_squid

delivery_app = typer.Typer(no_args_is_help=True)


@delivery_app.command("email")
def configure_email(
    squid: str = typer.Argument(..., help="Squid hash, name, or alias"),
    email: str = typer.Option(..., "--email", help="Email address"),
    notifications: bool = typer.Option(True, "--notifications/--no-notifications", help="Send notifications on completion"),
):
    """Configure email delivery for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.delivery.email(squid_id, email=email, notifications=notifications)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"Email delivery configured for {squid_id[:12]}")
    print_detail([
        ("Email", result.email),
        ("Notifications", result.notifications),
    ])


@delivery_app.command("googlesheet")
def configure_googlesheet(
    squid: str = typer.Argument(..., help="Squid hash, name, or alias"),
    url: str = typer.Option(..., "--url", help="Public Google Sheet URL"),
    append: bool = typer.Option(False, "--append/--no-append", help="Append results vs overwrite"),
    active: bool = typer.Option(True, "--active/--inactive", help="Enable/disable export"),
):
    """Configure Google Sheet delivery for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.delivery.google_sheet(squid_id, url=url, append=append, is_active=active)
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"Google Sheet delivery configured for {squid_id[:12]}")
    print_detail([
        ("URL", result.url),
        ("Append", result.append),
        ("Active", result.is_active),
    ])


@delivery_app.command("s3")
def configure_s3(
    squid: str = typer.Argument(..., help="Squid hash, name, or alias"),
    bucket: str = typer.Option(..., "--bucket", help="S3 bucket name"),
    target_path: str = typer.Option(..., "--target-path", help="Folder path inside bucket"),
    aws_access_key: Optional[str] = typer.Option(None, "--aws-access-key", help="AWS Access Key"),
    aws_secret_key: Optional[str] = typer.Option(None, "--aws-secret-key", help="AWS Secret Key"),
    active: bool = typer.Option(True, "--active/--inactive", help="Enable/disable export"),
):
    """Configure S3 delivery for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.delivery.s3(
        squid_id, bucket=bucket, target_path=target_path,
        aws_access_key=aws_access_key, aws_secret_key=aws_secret_key, is_active=active,
    )
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"S3 delivery configured for {squid_id[:12]}")
    print_detail([
        ("Bucket", result.bucket),
        ("Target Path", result.target_path),
        ("Active", result.is_active),
    ])


@delivery_app.command("webhook")
def configure_webhook(
    squid: str = typer.Argument(..., help="Squid hash, name, or alias"),
    url: str = typer.Option(..., "--url", help="Webhook endpoint URL"),
    retry: bool = typer.Option(True, "--retry/--no-retry", help="Retry failed deliveries"),
    on_running: bool = typer.Option(False, "--on-running", help="Subscribe to run start events"),
    on_paused: bool = typer.Option(False, "--on-paused", help="Subscribe to run pause events"),
    on_done: bool = typer.Option(True, "--on-done", help="Subscribe to run completion events"),
    on_error: bool = typer.Option(True, "--on-error", help="Subscribe to run error events"),
    active: bool = typer.Option(True, "--active/--inactive", help="Enable/disable webhook"),
):
    """Configure webhook delivery for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.delivery.webhook(
        squid_id, url=url, is_active=active, retry=retry,
        on_running=on_running, on_paused=on_paused, on_done=on_done, on_error=on_error,
    )
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"Webhook delivery configured for {squid_id[:12]}")
    print_detail([
        ("URL", result.url),
        ("Active", result.is_active),
        ("Retry", result.retry),
    ])


@delivery_app.command("sftp")
def configure_sftp(
    squid: str = typer.Argument(..., help="Squid hash, name, or alias"),
    host: str = typer.Option(..., "--host", help="SFTP server hostname"),
    port: int = typer.Option(22, "--port", help="SFTP port"),
    username: str = typer.Option(..., "--username", help="SFTP username"),
    password: str = typer.Option(..., "--password", help="SFTP password"),
    directory: str = typer.Option(..., "--directory", help="Target directory on server"),
    active: bool = typer.Option(True, "--active/--inactive", help="Enable/disable SFTP"),
):
    """Configure SFTP delivery for a squid."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    squid_id = _resolve_squid(client, squid)
    result = client.delivery.sftp(
        squid_id, host=host, port=port, username=username,
        password=password, directory=directory, is_active=active,
    )
    if _state.get("json"):
        print_json(asdict(result))
        return
    print_success(f"SFTP delivery configured for {squid_id[:12]}")
    print_detail([
        ("Host", result.host),
        ("Port", result.port),
        ("Username", result.username),
        ("Directory", result.directory),
        ("Active", result.is_active),
    ])


# --- Test commands ---


@delivery_app.command("test-email")
def test_email(email: str = typer.Option(..., "--email", help="Email address to test")):
    """Test email delivery configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delivery.test_email(email=email)
    if _state.get("json"):
        print_json(result)
        return
    if result.get("success"):
        print_success("Email delivery test passed")
    else:
        print_error("Email delivery test failed")
        raise typer.Exit(1)


@delivery_app.command("test-googlesheet")
def test_googlesheet(url: str = typer.Option(..., "--url", help="Google Sheet URL to test")):
    """Test Google Sheet delivery configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delivery.test_google_sheet(url=url)
    if _state.get("json"):
        print_json(result)
        return
    if result.get("success"):
        print_success("Google Sheet delivery test passed")
    else:
        print_error("Google Sheet delivery test failed")
        raise typer.Exit(1)


@delivery_app.command("test-s3")
def test_s3(
    bucket: str = typer.Option(..., "--bucket", help="S3 bucket name"),
    aws_access_key: Optional[str] = typer.Option(None, "--aws-access-key"),
    aws_secret_key: Optional[str] = typer.Option(None, "--aws-secret-key"),
):
    """Test S3 delivery configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delivery.test_s3(bucket=bucket, aws_access_key=aws_access_key, aws_secret_key=aws_secret_key)
    if _state.get("json"):
        print_json(result)
        return
    if result.get("success"):
        print_success("S3 delivery test passed")
    else:
        print_error("S3 delivery test failed")
        raise typer.Exit(1)


@delivery_app.command("test-webhook")
def test_webhook(url: str = typer.Option(..., "--url", help="Webhook URL to test")):
    """Test webhook delivery configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delivery.test_webhook(url=url)
    if _state.get("json"):
        print_json(result)
        return
    if result.get("success"):
        print_success("Webhook delivery test passed")
    else:
        print_error("Webhook delivery test failed")
        raise typer.Exit(1)


@delivery_app.command("test-sftp")
def test_sftp(
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(22, "--port"),
    username: str = typer.Option(..., "--username"),
    password: str = typer.Option(..., "--password"),
    directory: str = typer.Option(..., "--directory"),
):
    """Test SFTP delivery configuration."""
    from lobstr_cli.cli import get_client, _state
    client = get_client()
    result = client.delivery.test_sftp(
        host=host, port=port, username=username, password=password, directory=directory,
    )
    if _state.get("json"):
        print_json(result)
        return
    if result.get("success"):
        print_success("SFTP delivery test passed")
    else:
        print_error("SFTP delivery test failed")
        raise typer.Exit(1)

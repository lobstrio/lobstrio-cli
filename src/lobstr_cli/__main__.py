from lobstr_cli.cli import app
from lobstr_cli.client import APIError, AuthError, RateLimitError
from lobstr_cli.display import print_error


def main():
    try:
        app()
    except AuthError as e:
        print_error(f"Authentication failed: {e.message}")
        raise SystemExit(1)
    except RateLimitError as e:
        print_error(str(e))
        raise SystemExit(1)
    except APIError as e:
        print_error(str(e))
        raise SystemExit(1)


main()

import sys

from lobstr_cli.cli import app
from lobstr_cli.client import APIError
from lobstr_cli.display import print_error


def main():
    try:
        app()
    except APIError as e:
        print_error(str(e))
        sys.exit(1)


main()

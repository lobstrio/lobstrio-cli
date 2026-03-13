import sys

from lobstr_cli.cli import app
from lobstrio.exceptions import APIError
from lobstr_cli.display import print_error


def main():
    try:
        app()
    except APIError as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

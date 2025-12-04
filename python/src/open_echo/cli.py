import sys
from argparse import ArgumentParser

from open_echo.desktop import run_desktop
from open_echo.web import run_web


def main():
    parser = ArgumentParser(
        description="Command-line interface for the open_echo package."
    )
    parser.add_argument(
        "command", choices=["desktop", "web"], help="The command to run."
    )

    args = parser.parse_args()

    if args.command == "desktop":
        run_desktop()
    elif args.command == "web":
        run_web()
    else:
        print("Unknown command. Please use 'desktop' or 'web'.")
        sys.exit(1)


if __name__ == "__main__":
    main()

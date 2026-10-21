from argparse import ArgumentParser

from open_echo.desktop import run_desktop
from open_echo.simulate import run_simulate
from open_echo.UART_UDP_relay import configure_relay_parser, run_relay
from open_echo.web import run_web


def main():
    parser = ArgumentParser(
        description="Command-line interface for the open_echo package."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    desktop_parser = subparsers.add_parser("desktop", help="Run desktop interface")
    desktop_parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="URL of the web server (default: http://localhost:8000)",
    )
    desktop_parser.set_defaults(
        handler=lambda args: run_desktop(server_url=args.server_url)
    )

    web_parser = subparsers.add_parser("web", help="Run web interface")
    web_parser.set_defaults(handler=lambda _: run_web())

    relay_parser = subparsers.add_parser("relay", help="Run UART to UDP relay")
    configure_relay_parser(relay_parser)
    relay_parser.set_defaults(handler=run_relay)

    simulate_parser = subparsers.add_parser(
        "simulate", help="Generate simulated echo packets (UDP or serial PTY)"
    )
    simulate_parser.add_argument(
        "--host", default="127.0.0.1", help="UDP host to send to (default: 127.0.0.1)"
    )
    simulate_parser.add_argument(
        "--port", type=int, default=9999, help="UDP port to send to (default: 9999)"
    )
    simulate_parser.add_argument(
        "--rate", type=float, default=1.0, help="Packets per second (default: 1.0)"
    )
    simulate_parser.add_argument(
        "--num-samples", type=int, default=1800, help="Number of samples per packet"
    )
    simulate_parser.add_argument(
        "--randomize",
        action="store_true",
        help="Randomize depth index and spike amplitude",
    )
    simulate_parser.set_defaults(handler=lambda args: run_simulate(args))

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()

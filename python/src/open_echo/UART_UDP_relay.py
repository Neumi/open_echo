import argparse
import socket

import serial
import serial.tools.list_ports
from open_echo.echo import START_BYTE, compute_checksum, payload_size


def configure_relay_parser(parser):
    parser.add_argument(
        "-p",
        "--uart-port",
        help="UART device (e.g. COM3 or /dev/ttyUSB0)",
    )

    parser.add_argument(
        "-b",
        "--baud-rate",
        type=int,
        default=250000,
        help="UART baud rate (default: 250000)",
    )

    parser.add_argument(
        "-n",
        "--samples",
        type=int,
        default=1800,
        help="Number of samples per packet (default: 1800)",
    )

    parser.add_argument(
        "--udp-ip",
        default="127.0.0.1",
        help="UDP target IP (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--udp-port",
        type=int,
        default=5005,
        help="UDP target port (default: 5005)",
    )

    parser.add_argument(
        "--broadcast",
        action="store_true",
        help="Enable UDP broadcast (255.255.255.255)",
    )

    parser.add_argument(
        "--list-uart",
        action="store_true",
        help="List all available UART/serial ports and exit",
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all non-error output",
    )
    verbosity.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose packet diagnostics",
    )

    return parser


def list_uart_ports():
    """List all available UART/serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    print("Available UART ports:")
    for port in ports:
        print(f"  {port.device}  - {port.description}")


def read_raw_packet(ser, num_payload_bytes, verbose=False):
    """
    Reads and returns a FULL raw packet:
    b'\\xAA' + payload + checksum
    """
    while True:
        header = ser.read(1)
        if not header or header[0] != START_BYTE:
            continue

        payload = ser.read(num_payload_bytes)
        checksum = ser.read(1)

        if len(payload) != num_payload_bytes or len(checksum) != 1:
            if verbose:
                print("Incomplete packet")
            continue

        if compute_checksum(payload) != checksum[0]:
            if verbose:
                print("Checksum mismatch (UART)")
            continue

        if verbose:
            print("Packet received (checksum OK)")

        return header + payload + checksum


def run_relay(args=None):
    parser = None
    if args is None or isinstance(args, list):
        parser = configure_relay_parser(
            argparse.ArgumentParser(description="UART → UDP transparent relay")
        )
        args = parser.parse_args(args)

    # ===== Handle list-uart and exit =====
    if args.list_uart:
        list_uart_ports()
        return

    # Require UART port if not listing
    if not args.uart_port:
        print("Error: UART port must be specified with -p / --uart-port")
        if parser is not None:
            parser.print_help()
        return

    pld_size = payload_size(args.samples)
    udp_ip = "255.255.255.255" if args.broadcast else args.udp_ip

    # ===== Startup banner =====
    if not args.quiet:
        print("===================================")
        print(" UART → UDP Relay")
        print("===================================")
        print(f" UART port      : {args.uart_port}")
        print(f" Baud rate      : {args.baud_rate}")
        print(f" Samples        : {args.samples}")
        print(f" Payload size   : {pld_size} bytes")
        print(f" UDP target IP  : {udp_ip}")
        print(f" UDP target port: {args.udp_port}")
        print(f" Broadcast mode : {'ON' if args.broadcast else 'OFF'}")
        print(f" Verbose mode   : {'ON' if args.verbose else 'OFF'}")
        print(f" Quiet mode     : {'ON' if args.quiet else 'OFF'}")
        print("===================================\n")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if args.broadcast:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        with serial.Serial(args.uart_port, args.baud_rate, timeout=1) as ser:
            if not args.quiet:
                print("UART connected, relaying packets...\n")

            while True:
                packet = read_raw_packet(
                    ser, pld_size, verbose=args.verbose and not args.quiet
                )
                udp_sock.sendto(packet, (udp_ip, args.udp_port))

    except serial.SerialException as e:
        print(f"UART error: {e}")
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nRelay stopped by user")
    finally:
        udp_sock.close()

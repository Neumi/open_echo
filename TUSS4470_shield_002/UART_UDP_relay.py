import serial
import serial.tools.list_ports
import socket
import argparse

START_BYTE = 0xAA


def list_uart_ports():
    """List all available UART/serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    print("Available UART ports:")
    for port in ports:
        print(f"  {port.device}  - {port.description}")


def read_raw_packet(ser, payload_size, verbose=False):
    """
    Reads and returns a FULL raw packet:
    b'\\xAA' + payload + checksum
    """
    while True:
        header = ser.read(1)
        if header != bytes([START_BYTE]):
            continue

        payload = ser.read(payload_size)
        checksum = ser.read(1)

        if len(payload) != payload_size or len(checksum) != 1:
            if verbose:
                print("⚠️  Incomplete packet")
            continue

        # Verify checksum (XOR of payload bytes)
        calc_checksum = 0
        for b in payload:
            calc_checksum ^= b

        if calc_checksum != checksum[0]:
            if verbose:
                print("⚠️  Checksum mismatch (UART)")
            continue

        if verbose:
            print("📦 Packet received (checksum OK)")

        return header + payload + checksum


def main():
    parser = argparse.ArgumentParser(
        description="UART → UDP transparent relay"
    )

    parser.add_argument(
        "-p", "--uart-port",
        help="UART device (e.g. COM3 or /dev/ttyUSB0)"
    )

    parser.add_argument(
        "-b", "--baud-rate",
        type=int,
        default=250000,
        help="UART baud rate (default: 250000)"
    )

    parser.add_argument(
        "-n", "--samples",
        type=int,
        default=1800,
        help="Number of samples per packet (default: 1800)"
    )

    parser.add_argument(
        "--udp-ip",
        default="127.0.0.1",
        help="UDP target IP (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--udp-port",
        type=int,
        default=5005,
        help="UDP target port (default: 5005)"
    )

    parser.add_argument(
        "--broadcast",
        action="store_true",
        help="Enable UDP broadcast (255.255.255.255)"
    )

    parser.add_argument(
        "--list-uart",
        action="store_true",
        help="List all available UART/serial ports and exit"
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all non-error output"
    )
    verbosity.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose packet diagnostics"
    )

    args = parser.parse_args()

    # ===== Handle list-uart and exit =====
    if args.list_uart:
        list_uart_ports()
        return

    # Require UART port if not listing
    if not args.uart_port:
        print("❌ Error: UART port must be specified with -p / --uart-port")
        parser.print_help()
        return

    payload_size = 6 + 2 * args.samples
    udp_ip = "255.255.255.255" if args.broadcast else args.udp_ip

    # ===== Startup banner =====
    if not args.quiet:
        print("===================================")
        print(" UART → UDP Relay")
        print("===================================")
        print(f" UART port      : {args.uart_port}")
        print(f" Baud rate      : {args.baud_rate}")
        print(f" Samples        : {args.samples}")
        print(f" Payload size   : {payload_size} bytes")
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
                print("✅ UART connected, relaying packets...\n")

            while True:
                packet = read_raw_packet(
                    ser,
                    payload_size,
                    verbose=args.verbose and not args.quiet
                )
                udp_sock.sendto(packet, (udp_ip, args.udp_port))

    except serial.SerialException as e:
        print(f"❌ UART error: {e}")
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n🛑 Relay stopped by user")
    finally:
        udp_sock.close()


if __name__ == "__main__":
    main()

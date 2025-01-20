def parse_custom_protocol(packet: bytes) -> dict:
    """
    Parses a binary packet according to the specified protocol structure and returns a human-readable format.

    Parameters:
    packet (bytes): The binary data packet to be parsed.

    Returns:
    dict: A dictionary with the parsed packet information in human-readable format.
    """
    # Define sync bytes according to the observed packet
    expected_sync1 = 0x58  # Adjusted based on your packet example
    expected_sync2 = 0x02  # Adjusted based on your packet example

    # Minimum packet size (header and checksum bytes) without payload
    min_packet_size = 8
    if len(packet) < min_packet_size:
        raise ValueError("Invalid packet: too short to be a valid protocol packet")

    # Parse each field based on the given structure
    sync1 = packet[0]
    sync2 = packet[1]
    route = packet[2]
    mode = packet[3]
    packet_id = packet[4]
    length = packet[5]

    # Validate sync markers
    if sync1 != expected_sync1 or sync2 != expected_sync2:
        raise ValueError(
            f"Invalid packet: SYNC bytes do not match expected values ({expected_sync1:#04x}, {expected_sync2:#04x})")

    # Calculate the expected packet size based on the provided length
    expected_packet_size = min_packet_size + length
    actual_packet_size = len(packet)

    # Debug output to compare lengths
    print(
        f"Expected packet size: {expected_packet_size}, Actual packet size: {actual_packet_size}, Declared Length: {length}")

    # If there is a length mismatch, continue parsing for debugging purposes
    if actual_packet_size != expected_packet_size:
        print("Warning: LENGTH field does not match actual payload size. Proceeding with parsing.")

    # Extract payload and checksums
    payload = packet[6:6 + length]  # May not match length if there's a mismatch
    check1 = packet[6 + length] if 6 + length < actual_packet_size else None
    check2 = packet[7 + length] if 7 + length < actual_packet_size else None

    # Calculate checksum over all bytes between SYNC1 and PAYLOAD
    calculated_check1 = sum(packet[0:6 + length]) % 256
    calculated_check2 = (sum(packet[0:6 + length]) >> 8) % 256

    # Prepare the output in a readable format
    human_readable_packet = {
        "SYNC1": f"0x{sync1:02X}",
        "SYNC2": f"0x{sync2:02X}",
        "Route": f"0x{route:02X} (bitfield)",
        "Mode": f"0x{mode:02X} (bitfield)",
        "ID": f"0x{packet_id:02X}",
        "Length": length,
        "Payload": payload.hex() if payload else "N/A",
        "Check1": f"0x{check1:02X}" if check1 is not None else "Missing",
        "Check2": f"0x{check2:02X}" if check2 is not None else "Missing",
        "Valid Checksum": (
                    check1 == calculated_check1 and check2 == calculated_check2) if check1 and check2 else "Unable to validate"
    }

    return human_readable_packet


# Example usage:
packet = b'X\x02\n\x00\x00\x00\x1c\x11\x13\x11\x11\x1d\x11\x10\x0e\x1a\x17\x03\x15\r\x0c\x0b\x16\x1a\x16\x16\x17\x10\x15\x1c\x1a\x1b\x14\x1b\x16\x04\x07\x10\x0b\r\x16\x18\x15\x0f\x16\x0c\r\x11\x17\x12\x13\x14\x12\x0b\x17\x14\x15\x15\x17\x1b\x12\x1c\x13\x0b\n\x12\x0e\t\x08\r\x0b\r\x1a\x08\x0f\x16\x16\x10\x13\n\n\x13\x06\x18\x1a\x11\x1b\x1a\x12\r\x0f\x0b\x10\x10\n\x15\x0b\x0b\x18\x0b\x12\x12\x16\x12\x13\x10\x16\x10\x0c\x12\x1c\x14\x16\x1b\x14\x04\x1d\x12\x14\x0c\x11\x12\x1a$\r\x08\x19\x17\x06\r\x1b\x11\x11\x08\x10\x0b\x12\x14\x15\x15\n\x15\x10\x11\x18\x16\x1b\x16\n\x07\x07\x14\x12\x12\x0e\x1e\x15\x15\x18\x1b%\x1b\x1f\x1b\x16\x13\x14\r\x10\x13\x0e\n\x0b\x11\x0f\x11\x13\x07\x08\x17\x1a\x0f\x02\x15\x19\x18\x13\n\x1a\x17\x11\x0f\x13\x19\x13\x10\x15\x11\n\x08\x0b\x10\x10\x12\x14\x11'
parsed_packet = parse_custom_protocol(packet)
print(parsed_packet)

"""Human-readable and structured representations of received packets."""

from typing import Any

from .basic_packet import BasicPacketMessage


def basic_packet_to_dict(message: BasicPacketMessage) -> dict[str, Any]:
    """Return a JSON-friendly representation of a basic packet message."""
    return {
        "source_address": message.source_address,
        "destination_address": message.destination_address,
        "control_data": list(message.control_data),
        "payload": list(message.payload),
        "crc": list(message.crc) if message.crc is not None else None,
        "crc_valid": message.crc_valid,
        "rssi": message.rssi,
        "sqi": message.sqi,
        "pqi": message.pqi,
        "agc_word": message.agc_word,
    }


def to_dict(message: BasicPacketMessage) -> dict[str, Any]:
    """Return a JSON-friendly basic-packet dictionary.

    This short alias is useful when the formatter module is imported directly.
    """
    return basic_packet_to_dict(message)


def format_basic_packet(message: BasicPacketMessage, *, include_quality: bool = True) -> str:
    """Return a multi-line diagnostic representation of a basic packet."""
    lines = ["Message:"]
    if message.source_address is not None:
        lines.append(f"  Source Address:      0x{message.source_address:02x}")
    if message.destination_address is not None:
        lines.append(f"  Destination Address: 0x{message.destination_address:02x}")
    if message.control_data:
        lines.append("  Control Data: " + message.control_data.hex(" "))
    if message.crc:
        lines.append("  CRC Data:     " + message.crc.hex(" "))
    if message.crc_valid is not None:
        lines.append(f"  CRC Valid:    {message.crc_valid}")
    if include_quality and message.raw:
        lines.append(
            f"  RSSI: {message.rssi}  SQI: {message.sqi}  "
            f"PQI: {message.pqi}  AGC_WORD: {message.agc_word}"
        )
    lines.append("  Payload: " + message.payload.hex(" "))
    return "\n".join(lines) + "\n"


def format_basic_packet_one_line(message: BasicPacketMessage) -> str:
    """Return a compact hexadecimal representation of a basic packet."""
    fields = []
    if message.source_address is not None:
        fields.append(f"src={message.source_address:02x}")
    if message.destination_address is not None:
        fields.append(f"dst={message.destination_address:02x}")
    if message.control_data:
        fields.append(message.control_data.hex(" "))
    if message.payload:
        fields.append(message.payload.hex(" "))
    return " ".join(fields)

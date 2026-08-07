"""Experimental support for SPIRIT1 STack packets.

STack's automatic acknowledgement, retransmission, and sequence-number
behaviour has not been verified against hardware in this project.  Treat this
module as experimental until it has been exercised with compatible devices.
"""

import warnings
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .device import Spirit1Device
from .enums import CrcMode
from .receiver import ReceivedMessage
from .registers import Spirit1Registers


class ExperimentalStackPacketWarning(UserWarning):
    """STack packet functionality has not yet been validated on hardware."""


@dataclass
class StackPacketConfig:
    """Configuration for the experimental STack packet format.

    STack always transmits one destination and one source address byte.  The
    ``no_ack`` and ``auto_ack`` settings control SPIRIT1's protocol engine;
    their end-to-end behaviour remains unverified.
    """

    preamble_length: int = 1
    sync_words: Sequence[int] = field(default_factory=lambda: (0x01,))
    fixed_length: bool = False
    fixed_packet_length: int = 0
    length_width: int = 16
    crc_mode: CrcMode = CrcMode.CRC_MODE_OFF
    control_length: int = 0
    fec: bool = False
    data_whitening: bool = False
    no_ack: bool = False
    auto_ack: bool = False

    @property
    def sync_length(self) -> int:
        return len(self.sync_words)

    def validate(self) -> list[str]:
        errors = []
        if not 1 <= self.preamble_length <= 32:
            errors.append("Preamble length must be between 1 and 32 bytes")
        if not 1 <= self.sync_length <= 4:
            errors.append("Supply between 1 and 4 sync words")
        if any(not isinstance(word, int) or not 0 <= word <= 0xFF for word in self.sync_words):
            errors.append("Sync words must be byte values")
        if not 1 <= self.length_width <= 16:
            errors.append("Length width must be between 1 and 16 bits")
        if not isinstance(self.crc_mode, CrcMode):
            errors.append("CRC mode must be a CrcMode value")
        if not 0 <= self.control_length <= 4:
            errors.append("Control length must be between 0 and 4 bytes")
        if self.fixed_length and not 1 <= self.fixed_packet_length <= 0xFFFF:
            errors.append("Fixed packet length must be between 1 and 65535 bytes")
        return errors


@dataclass
class StackPacketMessage:
    """A received STack packet decoded from a :class:`ReceivedMessage`."""

    payload: bytes
    source_address: Optional[int]
    destination_address: Optional[int]
    control_data: bytes = b""
    crc: Optional[bytes] = None
    raw: Optional[ReceivedMessage] = None

    @property
    def crc_valid(self) -> Optional[bool]:
        return self.raw.crc_valid if self.raw else None


class StackPacket:
    """Apply and decode the experimental STack packet format.

    Transmission, automatic ACK/retry, and sequence-number handling should not
    be relied upon until verified with real STack devices.
    """

    def __init__(self, spirit: Spirit1Device, config: Optional[StackPacketConfig] = None):
        self.spirit = spirit
        self.config = config or StackPacketConfig()

    def apply(self) -> bool:
        """Apply STack framing settings, warning that hardware validation is pending."""
        if self.config.validate():
            return False
        warnings.warn(
            "STack packet support is experimental and unverified on hardware",
            ExperimentalStackPacketWarning,
            stacklevel=2,
        )
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 0, True)
        filter_options = self.spirit.read_register(Spirit1Registers.PKTFLT_OPTS) & 0xCE
        if self.config.crc_mode != CrcMode.CRC_MODE_OFF:
            filter_options |= 0x01
        self.spirit.write_registers(Spirit1Registers.PKTFLT_OPTS, filter_options)
        self.spirit.write_registers(
            Spirit1Registers.PKTCTRL_4,
            0x10 | self.config.control_length,  # ADDRESS_LEN = 2 for STack.
            0xC0 | (self.config.length_width - 1),  # PCKT_FRMT = STack.
            (self.config.preamble_length << 3)
            | ((self.config.sync_length - 1) << 1)
            | int(not self.config.fixed_length),
            (int(self.config.crc_mode) << 5)
            | (int(self.config.data_whitening) << 4)
            | int(self.config.fec),
        )
        self.spirit.write_registers(Spirit1Registers.SYNC_4, *reversed(self.config.sync_words))
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_2, 3, self.config.no_ack)
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_2, 2, self.config.auto_ack)
        return True

    def decode(self, raw_message: ReceivedMessage) -> StackPacketMessage:
        """Decode a captured receiver snapshot without reading hardware."""
        return StackPacketMessage(
            payload=bytes(raw_message.payload),
            source_address=raw_message.source_address,
            destination_address=raw_message.destination_address,
            control_data=raw_message.control_data[-self.config.control_length:] if self.config.control_length else b"",
            crc=self._decode_crc(raw_message),
            raw=raw_message,
        )

    def _decode_crc(self, raw_message: ReceivedMessage) -> Optional[bytes]:
        if self.config.crc_mode == CrcMode.CRC_MODE_OFF:
            return None
        length = 3
        if self.config.crc_mode == CrcMode.CRC_MODE_7:
            length = 1
        elif self.config.crc_mode in (CrcMode.CRC_MODE_1021, CrcMode.CRC_MODE_8005):
            length = 2
        return raw_message.crc[:length]

"""SPIRIT1 basic-packet configuration, decoding, and streaming."""

import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Sequence

from .enums import CrcMode
from .device import Spirit1Device
from .receiver import ReceivedMessage, Receiver
from .registers import Spirit1Registers


@dataclass
class BasicPacketConfig:
    preamble_length: int = 1
    sync_words: Sequence[int] = field(default_factory=lambda: (0x01,))
    fixed_length: bool = False
    fixed_packet_length: int = 0
    crc_mode: CrcMode = CrcMode.CRC_MODE_OFF
    control_length: int = 0
    address_field: bool = False
    fec: bool = False
    data_whitening: bool = False

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
        if not isinstance(self.crc_mode, CrcMode):
            errors.append("CRC mode must be a CrcMode value")
        if not 0 <= self.control_length <= 4:
            errors.append("Control length must be between 0 and 4 bytes")
        if self.fixed_length and not 1 <= self.fixed_packet_length <= 0xFFFF:
            errors.append("Fixed packet length must be between 1 and 65535 bytes")
        return errors


@dataclass
class BasicPacketMessage:
    """A decoded basic packet, or a message prepared for transmission."""

    payload: bytes
    source_address: Optional[int] = None
    destination_address: Optional[int] = None
    control_data: bytes = b""
    crc: Optional[bytes] = None
    raw: Optional[ReceivedMessage] = None

    @property
    def rssi(self) -> Optional[int]:
        return self.raw.rssi if self.raw else None

    @property
    def crc_valid(self) -> Optional[bool]:
        """Whether SPIRIT1 accepted this received packet's CRC, if known."""
        return self.raw.crc_valid if self.raw else None

    @property
    def sqi(self) -> Optional[int]:
        return self.raw.sqi if self.raw else None

    @property
    def pqi(self) -> Optional[int]:
        return self.raw.pqi if self.raw else None

    @property
    def agc_word(self) -> Optional[int]:
        return self.raw.agc_word if self.raw else None

class BasicPacket:
    """Applies :class:`BasicPacketConfig` and streams decoded basic packets."""

    def __init__(self, spirit: Spirit1Device, config: Optional[BasicPacketConfig] = None):
        self.spirit = spirit
        self.config = config or BasicPacketConfig()

    def apply(self) -> bool:
        if self.config.validate():
            return False
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 0, True)

        filter_options = self.spirit.read_register(Spirit1Registers.PKTFLT_OPTS) & 0xCE
        if self.config.crc_mode != CrcMode.CRC_MODE_OFF:
            filter_options |= 0x01
        self.spirit.write_registers(Spirit1Registers.PKTFLT_OPTS, filter_options)

        packet_control = [
            (int(self.config.address_field) << 3) | self.config.control_length,
            (self.config.fixed_packet_length.bit_length() - 1) & 0x0F,
            (self.config.preamble_length << 3)
            | ((self.config.sync_length - 1) << 1)
            | int(not self.config.fixed_length),
            (int(self.config.crc_mode) << 5)
            | (int(self.config.data_whitening) << 4)
            | int(self.config.fec),
        ]
        self.spirit.write_registers(Spirit1Registers.PKTCTRL_4, *packet_control)
        self.spirit.write_registers(Spirit1Registers.SYNC_4, *reversed(self.config.sync_words))
        return True

    async def receive(self, receiver: Receiver) -> AsyncIterator[BasicPacketMessage]:
        """Convert a raw receiver stream into a basic-packet stream."""
        async for raw_message in receiver.receive():
            yield self.decode(raw_message)

    def decode(self, raw_message: ReceivedMessage) -> BasicPacketMessage:
        """Convert an immutable received-message snapshot into a basic packet."""
        if self.config.address_field:
            source_address = raw_message.source_address
            destination_address = raw_message.destination_address
        else:
            source_address = destination_address = None
        return BasicPacketMessage(
            payload=bytes(raw_message.payload),
            source_address=source_address,
            destination_address=destination_address,
            control_data=raw_message.control_data[-self.config.control_length:] if self.config.control_length else b"",
            crc=self._decode_crc(raw_message),
            raw=raw_message,
        )

    def transmit(self, message: BasicPacketMessage, timeout: float = 1.0) -> bool:
        """Write a message to the TX FIFO and wait for transmission to finish."""
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")
        if self.config.address_field:
            if message.destination_address is None:
                raise ValueError("Basic packet address field is enabled, but no destination was supplied")
            self.spirit.write_registers(Spirit1Registers.RX_SOURCE_ADDR, message.destination_address)
            if message.source_address is not None:
                self.spirit.write_registers(Spirit1Registers.TX_SOURCE_ADDR, message.source_address)
        elif message.source_address is not None or message.destination_address is not None:
            raise ValueError("Packet addresses require address_field=True")
        self._write_control_data(message.control_data)
        if self.config.fixed_length:
            self._set_payload_length(len(message.payload))

        self.spirit.flush_tx_fifo()
        self.spirit.write_linear_fifo(message.payload)
        if not self.spirit.start_tx():
            return False
        deadline = time.monotonic() + timeout
        while self.spirit.linear_fifo_tx_size():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def _decode_crc(self, raw_message: ReceivedMessage) -> Optional[bytes]:
        if self.config.crc_mode == CrcMode.CRC_MODE_OFF:
            return None
        length = 3
        if self.config.crc_mode == CrcMode.CRC_MODE_7:
            length = 1
        elif self.config.crc_mode in (CrcMode.CRC_MODE_1021, CrcMode.CRC_MODE_8005):
            length = 2
        return raw_message.crc[:length]

    def _write_control_data(self, control_data: Sequence[int]) -> None:
        if not self.config.control_length:
            return
        if len(control_data) < self.config.control_length:
            raise ValueError("Not enough control-data bytes for the configured packet format")
        values = control_data[:self.config.control_length]
        if any(not isinstance(value, int) or not 0 <= value <= 0xFF for value in values):
            raise ValueError("Control data must contain byte values")
        register = Spirit1Registers.TX_CTRL_3 + (4 - self.config.control_length)
        self.spirit.write_registers(register, *values)

    def _set_payload_length(self, payload_length: int) -> None:
        total_length = payload_length + self.config.control_length + int(self.config.address_field)
        if not 0 <= total_length <= 0xFFFF:
            raise ValueError("Payload plus packet overhead must fit in 65535 bytes")
        self.spirit.write_registers(
            Spirit1Registers.PKTLEN_1,
            (total_length >> 8) & 0xFF,
            total_length & 0xFF,
        )

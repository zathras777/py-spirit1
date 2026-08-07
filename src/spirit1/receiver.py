"""Raw packet reception."""

import asyncio
import errno
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from .device import Spirit1Device
from .irq import IRQ, SpiritIrq
from .registers import Spirit1Registers

logger = logging.getLogger(__name__)


@dataclass
class ReceivedMessage:
    """RX FIFO bytes and the packet-status snapshot reported by SPIRIT1."""

    payload: bytearray = field(default_factory=bytearray)
    crc_valid: Optional[bool] = None
    rssi: Optional[int] = None
    sqi: Optional[int] = None
    pqi: Optional[int] = None
    agc_word: Optional[int] = None
    source_address: Optional[int] = None
    destination_address: Optional[int] = None
    control_data: bytes = b""
    crc: bytes = b""

    def update_quality(self, spirit: Spirit1Device) -> None:
        values = spirit.read_register_block(Spirit1Registers.LINK_QUALIF_2, 3)
        self.sqi = values[1] & 0x7F
        self.pqi = values[0] & 0x7F
        self.agc_word = values[2] & 0x0F
        self.rssi = spirit.read_register(Spirit1Registers.RSSI_LEVEL)

    def update_packet_status(self, spirit: Spirit1Device) -> None:
        """Snapshot packet fields before another received frame can replace them."""
        values = spirit.read_register_block(Spirit1Registers.CRC_FIELD_2, 9)
        self.crc = bytes(reversed(values[:3]))
        self.control_data = bytes(values[3:7])
        self.source_address = values[7]
        self.destination_address = values[8]


class Receiver:
    """Yield raw :class:`ReceivedMessage` objects from the RX FIFO."""

    def __init__(
        self,
        spirit: Spirit1Device,
        irq: IRQ,
        poll_interval: float = 0.01,
        ignore_invalid_crc: bool = True,
    ):
        if poll_interval < 0:
            raise ValueError("Poll interval must not be negative")
        self.spirit = spirit
        self.irq = irq
        self.poll_interval = poll_interval
        self.ignore_invalid_crc = ignore_invalid_crc
        self.should_run = True
        self.debug = False

    def get_persistent_rx(self) -> bool:
        return self.spirit.get_register_bit(Spirit1Registers.PROTOCOL_0, 1)

    def set_persistent_rx(self, enabled: bool) -> None:
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_0, 1, enabled)

    def stop(self) -> None:
        """Stop receiving and return the radio to READY while SPI is available."""
        if not self.should_run:
            return
        self.should_run = False
        self.spirit.sabort()

    async def receive(self) -> AsyncIterator[ReceivedMessage]:
        buffer = bytearray()
        self.should_run = True
        if not self.spirit.flush_rx_fifo():
            raise RuntimeError("Unable to flush the RX FIFO")
        if not self.spirit.start_rx():
            raise RuntimeError("Unable to enter RX state")

        try:
            while self.should_run:
                status = self.irq.get_status()
                if self.debug and status and status != SpiritIrq.RSSI_ABOVE_TH.value:
                    logger.debug("IRQ status: %#010x", status)

                if IRQ.check_flag(status, SpiritIrq.RX_FIFO_ALMOST_FULL):
                    buffer.extend(self._read_fifo())
                if IRQ.check_flag(status, SpiritIrq.RX_TIMEOUT):
                    logger.info("RX timeout received")
                    break
                if IRQ.check_flag(status, SpiritIrq.RX_DATA_READY):
                    buffer.extend(self._read_fifo())
                    message = ReceivedMessage(
                        buffer,
                        crc_valid=not IRQ.check_flag(status, SpiritIrq.CRC_ERROR),
                    )
                    message.update_quality(self.spirit)
                    message.update_packet_status(self.spirit)
                    if message.crc_valid or not self.ignore_invalid_crc:
                        yield message
                    else:
                        logger.debug("Discarding received message with an invalid CRC")
                    buffer = bytearray()
                    if self.should_run:
                        self.spirit.sabort()
                        self.spirit.flush_rx_fifo()
                        self.spirit.start_rx()

                await asyncio.sleep(self.poll_interval)
        finally:
            if self.should_run:
                self.should_run = False
                try:
                    self.spirit.sabort()
                except OSError as error:
                    # An owning application may close SPI while asyncio is
                    # finalising this generator during shutdown.
                    if error.errno != errno.EBADF:
                        raise
                    logger.debug("SPI was already closed during receiver cleanup")

    def _read_fifo(self) -> bytearray:
        size = self.spirit.linear_fifo_rx_size()
        return self.spirit.read_linear_fifo(size) if size else bytearray()

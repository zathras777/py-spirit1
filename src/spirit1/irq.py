"""Interrupt definitions, configuration, and status access."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .device import Spirit1Device
from .registers import Spirit1Registers


class SpiritIrq(Enum):
    RX_DATA_READY = 1 << 0
    RX_DATA_DISC = 1 << 1
    TX_DATA_SENT = 1 << 2
    MAX_RE_TX_REACH = 1 << 3
    CRC_ERROR = 1 << 4
    TX_FIFO_ERROR = 1 << 5
    RX_FIFO_ERROR = 1 << 6
    TX_FIFO_ALMOST_FULL = 1 << 7
    TX_FIFO_ALMOST_EMPTY = 1 << 8
    RX_FIFO_ALMOST_FULL = 1 << 9
    RX_FIFO_ALMOST_EMPTY = 1 << 10
    MAX_BO_CCA_REACH = 1 << 11
    VALID_PREAMBLE = 1 << 12
    VALID_SYNC = 1 << 13
    RSSI_ABOVE_TH = 1 << 14
    WKUP_TOUT_LDC = 1 << 15
    READY = 1 << 16
    STANDBY_DELAYED = 1 << 17
    LOW_BATT_LVL = 1 << 18
    POR = 1 << 19
    BOR = 1 << 20
    LOCK = 1 << 21
    PM_COUNT_EXPIRED = 1 << 22
    XO_COUNT_EXPIRED = 1 << 23
    SYNTH_LOCK_TIMEOUT = 1 << 24
    SYNTH_LOCK_STARTUP = 1 << 25
    SYNTH_CAL_TIMEOUT = 1 << 26
    TX_START_TIME = 1 << 27
    RX_START_TIME = 1 << 28
    RX_TIMEOUT = 1 << 29
    AES_END = 1 << 30


@dataclass
class IRQConfig:
    enabled: set[SpiritIrq] = field(default_factory=set)

    @property
    def mask(self) -> int:
        return sum(irq.value for irq in self.enabled)


class IRQ:
    """Applies :class:`IRQConfig` and reads interrupt status."""

    def __init__(self, spirit: Spirit1Device, config: IRQConfig|None = None):
        self.spirit: Spirit1Device = spirit
        self.config: IRQConfig = config or IRQConfig()

    def apply(self) -> None:
        mask = self.config.mask
        values = [(mask >> (8 * index)) & 0xFF for index in range(3, -1, -1)]
        _ = self.spirit.write_registers(Spirit1Registers.IRQ_MASK_3, *values)

    def get_status(self) -> int:
        status = self.spirit.read_register_block(
            Spirit1Registers.IRQ_STATUS_3,
            4,
        )
        return sum(value << (8 * (3 - index)) for index, value in enumerate(status))

    @staticmethod
    def check_flag(status: int, flag: SpiritIrq) -> bool:
        return (status & flag.value) == flag.value

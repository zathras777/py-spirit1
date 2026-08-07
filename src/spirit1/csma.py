"""CSMA configuration."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from .device import Spirit1Device
from .registers import Spirit1Registers


class CCAPeriod(IntEnum):
    TBitTime_64 = 0
    TBitTime_128 = 1
    TBitTime_256 = 2
    TBitTime_512 = 3


class CCALength(IntEnum):
    CcaTime_0 = 0
    CcaTime_1 = 0x10
    CcaTime_2 = 0x20
    CcaTime_3 = 0x30
    CcaTime_4 = 0x40
    CcaTime_5 = 0x50
    CcaTime_6 = 0x60
    CcaTime_7 = 0x70
    CcaTime_8 = 0x80
    CcaTime_9 = 0x90
    CcaTime_10 = 0xA0
    CcaTime_11 = 0xB0
    CcaTime_12 = 0xC0
    CcaTime_13 = 0xD0
    CcaTime_14 = 0xE0
    CcaTime_15 = 0xF0


@dataclass
class CSMAConfig:
    enabled: bool = False
    persist: bool = False
    cca_period: CCAPeriod = CCAPeriod.TBitTime_64
    cca_length: CCALength = CCALength.CcaTime_0
    max_backoffs: int = 0
    backoff_counter_seed: int = 0xFF00
    backoff_prescaler: int = 1

    def validate(self) -> list[str]:
        errors = []
        if not 0 <= self.max_backoffs <= 7:
            errors.append("Maximum backoffs must be between 0 and 7")
        if not 0 <= self.backoff_counter_seed <= 0xFFFF:
            errors.append("Backoff counter seed must be a 16-bit value")
        if not 0 <= self.backoff_prescaler <= 0x3F:
            errors.append("Backoff prescaler must be between 0 and 63")
        return errors


class CSMA:
    """Applies :class:`CSMAConfig` to the device."""

    def __init__(self, spirit: Spirit1Device, config: Optional[CSMAConfig] = None):
        self.spirit = spirit
        self.config = config or CSMAConfig()

    def apply(self) -> bool:
        if self.config.validate():
            return False
        seed = self.config.backoff_counter_seed
        registers = [
            (seed >> 8) & 0xFF,
            seed & 0xFF,
            ((self.config.backoff_prescaler & 0x3F) << 2) | self.config.cca_period.value,
            self.config.cca_length.value | self.config.max_backoffs,
        ]
        self.spirit.write_registers(Spirit1Registers.CSMA_CONFIG_3, *registers)
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 2, self.config.persist)
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 1, self.config.enabled)
        return True

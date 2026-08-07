"""Signal quality indicator configuration."""

from dataclasses import dataclass
from typing import Optional

from .device import Spirit1Device
from .registers import Spirit1Registers


@dataclass
class QIConfig:
    sqi_threshold: int = 0
    sqi_enabled: bool = False
    pqi_threshold: int = 0
    pqi_enabled: bool = False

    def validate(self) -> list[str]:
        errors = []
        if not 0 <= self.sqi_threshold <= 3:
            errors.append("SQI threshold must be between 0 and 3")
        if not 0 <= self.pqi_threshold <= 15:
            errors.append("PQI threshold must be between 0 and 15")
        return errors


class QI:
    """Applies :class:`QIConfig` and reads received signal-quality values."""

    def __init__(self, spirit: Spirit1Device, config: Optional[QIConfig] = None):
        self.spirit = spirit
        self.config = config or QIConfig()

    def apply(self) -> bool:
        if self.config.validate():
            return False
        value = (
            (self.config.sqi_threshold << 6)
            | (self.config.pqi_threshold << 2)
            | (int(self.config.sqi_enabled) << 1)
            | int(self.config.pqi_enabled)
        )
        self.spirit.write_registers(Spirit1Registers.QI, value)
        return True

    def sqi_value(self) -> int:
        return self.spirit.read_register(Spirit1Registers.LINK_QUALIF_1) & 0x7F

    def pqi_value(self) -> int:
        return self.spirit.read_register(Spirit1Registers.LINK_QUALIF_2) & 0x7F

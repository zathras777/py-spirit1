import logging

from . import Spirit1
from .registers import Spirit1Registers

logger = logging.getLogger(__name__)

class QI:
    def __init__(self, spirit:Spirit1):
        self.spirit = spirit

    def sqi_set_threshold(self, thresh:int):
        if not 0 <= thresh <= 3:
            logger.warning("Invalid SQI Threshold value passed. Must be between 0 and 3.")
            return
        self.spirit.update_register(Spirit1Registers.QI, 0x3F, thresh << 6)

    def sqi_enable(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.QI, 1, onoff)

    def sqi_get_threshold(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.QI)[0] >> 1

    def sqi_value(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.LINK_QUALIF_1)[0] & 0x7F

    def pqi_set_threshold(self, thresh:int):
        if not 0 <= thresh <= 15:
            logger.warning("Invalid SQI Threshold value passed. Must be between 0 and 15.")
            return
        self.spirit.update_register(Spirit1Registers.QI, 0xC3, thresh << 2)

    def pqi_enable(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.QI, 0, onoff)

    def pqi_get_threshold(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.QI)[0] & 0x3C

    def pqi_value(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.LINK_QUALIF_2)[0]
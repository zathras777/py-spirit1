from enum import IntEnum

from . import Spirit1
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
    CcaTime_10 = 0xa0
    CcaTime_11 = 0xb0
    CcaTime_12 = 0xc0
    CcaTime_13 = 0xd0
    CcaTime_14 = 0xe0
    CcaTime_15 = 0xf0


class CSMA:
    def __init__(self, spirit:Spirit1):
        self.spirit:Spirit1 = spirit
        self.persist:bool = False
        self.cca_period:CCAPeriod = CCAPeriod.TBitTime_64
        self.cca_length:CCALength = CCALength.CcaTime_0
        self.c_max_nb:int = 0
        self.bu_counter_seed:int = 0xff00
        self.bu_prescaler:int = 1

    def set_period(self, val:int):
        if val == 64:
            self.cca_period = CCAPeriod.TBitTime_64
        elif val == 128:
            self.cca_period = CCAPeriod.TBitTime_128
        elif val == 256:
            self.cca_period = CCAPeriod.TBitTime_256
        elif val == 512:
            self.cca_period = CCAPeriod.TBitTime_512
        else:
            self.cca_period = CCAPeriod.TBitTime_64

    def enable(self):
        regs = [self.bu_counter_seed & 0xff00, 
                self.bu_counter_seed & 0xff,
                (self.bu_prescaler & 0x3f << 2) | (self.cca_period.value & 0x03),
                self.cca_length.value | (self.c_max_nb & 0x7)]
        self.spirit.write_registers(Spirit1Registers.CSMA_CONFIG_3, *regs)
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 2, self.persist)
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 1, True)

    def disable(self):
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 1, False)


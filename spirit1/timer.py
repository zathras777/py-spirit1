from typing import Tuple

from . import Spirit1
from .registers import Spirit1Registers
from .radio import DOUBLE_XTAL_THR

class Timer:
    def __init__(self, spirit:Spirit1, xtal:int):
        self.spirit = spirit
        self.xtal = xtal   # MUST be same as configured for Radio
        self.and_or:bool = False  # True = OR, False = AND

    def set_rx_timeout_stop_conditions(self, sqi:bool=True, pqi:bool=False, rssi:bool=False):
        val:int = (sqi << 6) + (pqi << 5) + (rssi << 7)
        self.spirit.update_register(Spirit1Registers.PROTOCOL_2, 0x1F, val)
        self.spirit.set_register_bit(Spirit1Registers.PKTFLT_OPTS, 7, self.and_or)

    def set_rx_timeout_counter(self, counter:int):
        self.spirit.write_registers(Spirit1Registers.TIMERS_4, (counter & 0xff))

    def set_rx_timeout_prescaler(self, scaler:int):
        self.spirit.write_registers(Spirit1Registers.TIMERS_5, (scaler & 0xff))

    def timer_get_rco_frequency(self) -> int:
        rco_freq:int = 34700
        if self.xtal == 50000000:
            if self.spirit.get_register_bit(0x01, 6):
                rco_freq = 36100
            else:
                rco_freq = 33300
        return rco_freq

    def timer_compute_wakeup_values(self, ms:int) -> Tuple[int, int]:
        rco_freq = self.timer_get_rco_frequency() / 1000
        n = ms * rco_freq
        if n / 0xFF > 0xFD:
            # Return the max permitted values as value cannot be set
            return 0xff, 0xff
        pscaler = (n / 0xFF) + 2
        counter = n / pscaler

        err = abs((counter * pscaler) / rco_freq - ms)
        if counter <= 0xfe and abs(((counter + 1) * pscaler) / rco_freq - ms) < err:
            counter += 1
        pscaler -= 1
        counter = 1 if counter < 1 else counter - 1
        return counter, pscaler

    def timer_compute_rx_timeout_values(self, ms:int) -> Tuple[int, int]:
        xtal = self.xtal
        if xtal > DOUBLE_XTAL_THR:
            xtal >>= 1
        n = ms * xtal / 1210000
        if n / 0xFF > 0xFD:
            # Return the max permitted values as value cannot be set
            return 0xff, 0xff
        pscaler = (n / 0xFF) + 2
        counter = n / pscaler
        err = abs(counter * pscaler * 1210000 / xtal - ms)
        if counter <= 0xfe and abs((counter + 1) * pscaler * 1210000 / xtal - ms) < err:
            counter += 1
        pscaler -= 1
        counter = 1 if counter < 1 else counter - 1
        return int(counter) & 0xff, int(pscaler) & 0xff

    def timer_set_rx_timeout_ms(self, ms:int):
        vals = self.timer_compute_rx_timeout_values(ms)
        self.spirit.write_registers(Spirit1Registers.TIMERS_5, *vals)

#    def timer_set_rx_timeout_stop_condition(self, stop:RxTimeoutStopCondition):
#        if not stop in RxTimeoutStopCondition:
#            logger.warning("Invalid RX timeout stop condition. Use one of the RxTimeoutStopCondition constants.")
#        vals = self.spirit.read_registers(0x4F, 0x50)
##            return
#        vals[0] = (vals[0] & 0xBF) + ((stop.value & 0x08) << 3)
#        vals[1] = (vals[1] & 0x1F) + (stop.value << 5)
#        self.spirit.write_registers(0x4F, *vals)

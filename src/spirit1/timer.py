"""Receiver timeout configuration and timer calculations."""

from dataclasses import dataclass

from .device import Spirit1Device
from .radio import DOUBLE_XTAL_THR
from .registers import Spirit1Registers


@dataclass
class TimerConfig:
    xtal_frequency: int
    timeout_counter: int = 0
    timeout_prescaler: int = 0
    stop_on_sqi: bool = True
    stop_on_pqi: bool = False
    stop_on_rssi: bool = False
    stop_conditions_or: bool = False

    def validate(self) -> list[str]:
        errors = []
        if self.xtal_frequency <= 0:
            errors.append("XTAL frequency must be greater than zero")
        if not 0 <= self.timeout_counter <= 0xFF:
            errors.append("Timeout counter must be an 8-bit value")
        if not 0 <= self.timeout_prescaler <= 0xFF:
            errors.append("Timeout prescaler must be an 8-bit value")
        return errors


class Timer:
    """Applies :class:`TimerConfig` and calculates SPIRIT1 timer values."""

    def __init__(self, spirit: Spirit1Device, config: TimerConfig):
        self.spirit = spirit
        self.config = config

    def apply(self) -> bool:
        if self.config.validate():
            return False
        stop_conditions = (
            (int(self.config.stop_on_rssi) << 7)
            | (int(self.config.stop_on_sqi) << 6)
            | (int(self.config.stop_on_pqi) << 5)
        )
        self.spirit.update_register(Spirit1Registers.PROTOCOL_2, 0x1F, stop_conditions)
        self.spirit.set_register_bit(Spirit1Registers.PKTFLT_OPTS, 7, self.config.stop_conditions_or)
        self.spirit.write_registers(
            Spirit1Registers.TIMERS_5,
            self.config.timeout_prescaler,
            self.config.timeout_counter,
        )
        return True

    def timer_get_rco_frequency(self) -> int:
        rco_frequency = 34_700
        if self.config.xtal_frequency == 50_000_000:
            rco_frequency = 36_100 if self.spirit.get_register_bit(0x01, 6) else 33_300
        return rco_frequency

    def timer_compute_wakeup_values(self, milliseconds: int) -> tuple[int, int]:
        rco_frequency = self.timer_get_rco_frequency() / 1_000
        n = milliseconds * rco_frequency
        if n / 0xFF > 0xFD:
            return 0xFF, 0xFF
        prescaler = int(n / 0xFF) + 2
        counter = n / prescaler
        if counter <= 0xFE and abs(((counter + 1) * prescaler) / rco_frequency - milliseconds) < abs(
            (counter * prescaler) / rco_frequency - milliseconds
        ):
            counter += 1
        return max(1, int(counter) - 1), prescaler - 1

    def set_rx_timeout_ms(self, milliseconds: int) -> bool:
        counter, prescaler = self.timer_compute_rx_timeout_values(milliseconds)
        self.config.timeout_counter = counter
        self.config.timeout_prescaler = prescaler
        return self.apply()

    def timer_compute_rx_timeout_values(self, milliseconds: int) -> tuple[int, int]:
        xtal = self.config.xtal_frequency
        if xtal > DOUBLE_XTAL_THR:
            xtal >>= 1
        n = milliseconds * xtal / 1_210_000
        if n / 0xFF > 0xFD:
            return 0xFF, 0xFF
        prescaler = int(n / 0xFF) + 2
        counter = n / prescaler
        if counter <= 0xFE and abs((counter + 1) * prescaler * 1_210_000 / xtal - milliseconds) < abs(
            counter * prescaler * 1_210_000 / xtal - milliseconds
        ):
            counter += 1
        return max(1, int(counter) - 1), prescaler - 1

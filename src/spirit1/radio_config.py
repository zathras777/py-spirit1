"""Declarative configuration for a SPIRIT1 radio."""

from dataclasses import dataclass
from typing import Optional

from .enums import Spirit1Modulation
from .frequency import Frequency


@dataclass
class RadioConfig:
    """Settings that can be validated before they are applied to hardware."""

    xtal_frequency: int = 26_000_000
    base_frequency: int = 868_000_000
    channel_space: int = 20_000
    channel_number: int = 0
    modulation: Spirit1Modulation = Spirit1Modulation.GFSK_BT1
    datarate: int = 50_000
    freq_deviation: int = 20_000
    bandwidth: int = 100_000
    frequency_offset: int = 0
    # None preserves the divider configured in the device. Set a boolean to
    # explicitly override it during Radio.init_device().
    reference_divider: Optional[bool] = None
    digital_divider: bool = False

    @property
    def frequency_base(self) -> Frequency:
        """Return the configured base frequency as a calculation value object."""
        return Frequency(self.base_frequency)

    @frequency_base.setter
    def frequency_base(self, frequency: Frequency) -> None:
        self.base_frequency = frequency.frequency

    def validate(self) -> list[str]:
        """Return validation errors without touching the radio hardware."""
        errors = []
        if self.xtal_frequency <= 0:
            errors.append("XTAL frequency must be greater than zero")
        if not 100 < self.datarate < 510_000:
            errors.append("Datarate must be between 100 and 510000")
        if not self.frequency_base.is_possible():
            errors.append("Base frequency is outside the permitted bands")
        if not 0 <= self.channel_number <= 0xFF:
            errors.append("Channel number must be between 0 and 255")
        if self.channel_space < 0:
            errors.append("Channel space must not be negative")
        if self.freq_deviation < 0:
            errors.append("Frequency deviation must not be negative")
        if self.bandwidth <= 0:
            errors.append("Bandwidth must be greater than zero")
        if not isinstance(self.modulation, Spirit1Modulation):
            errors.append("Modulation must be a Spirit1Modulation value")
        return errors

    def as_dict(self) -> dict:
        """Return a serializable snapshot of user-facing radio settings."""
        return {
            "xtal_frequency": self.xtal_frequency,
            "base_frequency": self.base_frequency,
            "channel_space": self.channel_space,
            "channel_number": self.channel_number,
            "modulation": self.modulation,
            "datarate": self.datarate,
            "freq_deviation": self.freq_deviation,
            "bandwidth": self.bandwidth,
            "frequency_offset": self.frequency_offset,
        }

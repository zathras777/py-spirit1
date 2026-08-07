"""Type contract for SPI transports supported by :class:`Spirit1Device`."""

from typing import Protocol, Sequence


class SpiDevice(Protocol):
    """Minimal SPI interface required by the SPIRIT1 driver.

    ``spidev.SpiDev`` satisfies this contract, as can a test double or another
    platform-specific SPI adapter.
    """

    def xfer2(self, values: Sequence[int]) -> Sequence[int]:
        """Transfer bytes and return the bytes received from the device."""

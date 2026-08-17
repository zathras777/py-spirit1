"""Optional convenience support for Linux's :mod:`spidev` package."""

from typing import Optional

from .device import Spirit1Device
from .gpio import ShutdownPin


def open_spidev(
    bus: int = 0,
    device: int = 0,
    speed_hz: int = 250_000,
    mode: int = 0b00,
    sdn: Optional[ShutdownPin] = None,
) -> Spirit1Device:
    """Open a Linux SPI device and return a configured :class:`Spirit1Device`.

    ``spidev`` is imported only when this helper is called, so applications
    using another SPI adapter do not need the optional hardware dependency.
    Call :meth:`Spirit1Device.close` when finished.
    """
    if bus < 0 or device < 0:
        raise ValueError("SPI bus and device numbers must not be negative")
    if speed_hz <= 0:
        raise ValueError("SPI speed must be greater than zero")
    if not 0 <= mode <= 0b11:
        raise ValueError("SPI mode must be between 0 and 3")
    try:
        import spidev
    except ImportError as error:
        raise RuntimeError(
            "open_spidev() requires the optional 'spidev' dependency; "
            "install spirit1[hardware]"
        ) from error

    spi = spidev.SpiDev()
    try:
        spi.open(bus, device)
        spi.max_speed_hz = speed_hz
        spi.mode = mode
        return Spirit1Device(spi, sdn=sdn)
    except BaseException:
        spi.close()
        raise

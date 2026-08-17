"""Optional GPIO adapters for hardware signals outside the SPI bus."""

from typing import Optional, Protocol


class ShutdownPin(Protocol):
    """Active-high SPIRIT1 SDN control pin."""

    def get_value(self) -> bool:
        """Return ``True`` when SDN is high and the radio is shut down."""

    def set_value(self, value: bool) -> None:
        """Drive SDN high (shutdown) or low (operate)."""


class GpioZeroShutdownPin:
    """Adapt a :class:`gpiozero.OutputDevice` to :class:`ShutdownPin`."""

    def __init__(self, output_device) -> None:
        self._output_device = output_device

    def get_value(self) -> bool:
        return bool(self._output_device.value)

    def set_value(self, value: bool) -> None:
        self._output_device.value = value

    def close(self) -> None:
        self._output_device.close()


def open_gpiozero_sdn(pin: int = 4, *, initial_value: Optional[bool] = None) -> GpioZeroShutdownPin:
    """Open an active-high SDN pin using optional :mod:`gpiozero` support.

    The default ``initial_value=None`` preserves the existing pin state rather
    than unexpectedly waking the radio.  GPIO4 is physical header pin 7.
    """
    try:
        from gpiozero import OutputDevice
    except ImportError as error:
        raise RuntimeError(
            "open_gpiozero_sdn() requires the optional 'gpiozero' dependency; "
            "install spirit1[gpio]"
        ) from error
    return GpioZeroShutdownPin(
        OutputDevice(pin, active_high=True, initial_value=initial_value),
    )

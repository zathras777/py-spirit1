"""Optional GPIO adapters for hardware signals outside the SPI bus."""

from __future__ import annotations

from typing import Protocol


class ShutdownPin(Protocol):
    """Active-high SPIRIT1 SDN control pin."""

    def get_value(self) -> bool|None:
        """Return ``True`` when SDN is high and the radio is shut down."""

    def set_value(self, value: bool) -> None:
        """Drive SDN high (shutdown) or low (operate)."""

class _OutputDevice(Protocol):
    @property
    def value(self) -> float: ...

    @value.setter
    def value(self, value: float) -> None: ...

    def close(self) -> None: ...


class GpioZeroShutdownPin:
    """Adapt a :class:`gpiozero.OutputDevice` to :class:`ShutdownPin`."""

    def __init__(self, output_device: _OutputDevice) -> None:
        self._output_device: _OutputDevice = output_device

    def get_value(self) -> bool:
        return bool(self._output_device.value)

    def set_value(self, value: bool) -> None:
        self._output_device.value = value

    def close(self) -> None:
        self._output_device.close()


def open_gpiozero_sdn(pin: int = 4, *, initial_value: bool|None = None) -> GpioZeroShutdownPin:
    """Open an active-high SDN pin using optional :mod:`gpiozero` support.

    The default ``initial_value=None`` preserves the existing pin state rather
    than unexpectedly waking the radio.  GPIO4 is physical header pin 7.
    """
    try:
        from gpiozero import OutputDevice
    except ImportError as error:
        raise RuntimeError(
            "open_gpiozero_sdn() requires the optional 'gpiozero' dependency; " +
            "install spirit1[gpio]"
        ) from error
    return GpioZeroShutdownPin(
        OutputDevice(pin, active_high=True, initial_value=initial_value),
    )

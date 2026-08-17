from __future__ import annotations

import logging
import time
from typing import AnyStr, Union

from .enums import Spirit1Commands, Spirit1State
from .gpio import ShutdownPin
from .registers import Spirit1Registers
from .spi import SpiDevice
from .status import Spirit1Status

logger = logging.getLogger(__name__)

# Keep this alias compatible with Python 3.9, which is still supported by the
# package.  ``Spirit1Registers | int`` is only evaluated successfully on 3.10+.
Register = Union[Spirit1Registers, int]


class Spirit1Device:
    """Low-level SPIRIT1 device driver backed by an SPI transport."""

    def __init__(self, spi: SpiDevice, sdn: ShutdownPin|None = None):
        self._spi: SpiDevice = spi
        self._sdn: ShutdownPin|None = sdn
        self.is_closed:bool = False
        self.debug_spi:bool = False
        self.debug_spi_tx:bool = False
        self.status: Spirit1Status = Spirit1Status()

        if self.check_communication() and self.status.state == Spirit1State.LOCKWON:
            _ = self.reset()

    def close(self) -> None:
        """Close an owned SPI transport when it provides a ``close`` method."""
        if self.is_closed:
            return
        self.is_closed = True
        close = getattr(self._spi, "close", None)
        if callable(close):
            _ = close()

    def is_shutdown(self) -> bool|None:
        """Return whether the optional active-high SDN pin is asserted."""
        return self._sdn is not None and self._sdn.get_value()

    def shutdown(self) -> None:
        """Assert SDN, fully powering down SPIRIT1 and losing configuration."""
        self._require_sdn().set_value(True)

    def wake(self, startup_delay: float = 0.001) -> bool:
        """Deassert SDN, wait for startup, and verify that SPI responds."""
        if startup_delay < 0:
            raise ValueError("Startup delay must not be negative")
        self._require_sdn().set_value(False)
        time.sleep(startup_delay)
        return self.check_communication()

    def hardware_reset(self, shutdown_delay: float = 0.001, startup_delay: float = 0.001) -> bool:
        """Pulse SDN high then low, resetting hardware and erasing configuration."""
        if shutdown_delay < 0 or startup_delay < 0:
            raise ValueError("Reset delays must not be negative")
        self.shutdown()
        time.sleep(shutdown_delay)
        return self.wake(startup_delay)

    def check_communication(self) -> bool:
        """Perform a read-only status transaction without waking a shut-down radio."""
        if self.is_shutdown():
            return False
        try:
            return self.refresh_status()
        except (OSError, IndexError, ValueError):
            return False

    # State Functions
    def reset(self) -> bool:
        return self._change_state(Spirit1Commands.SRES, Spirit1State.READY)

    def is_standby(self) -> bool:
        return self.status.state == Spirit1State.STANDBY

    def standby(self) -> bool:
        return self._change_state(Spirit1Commands.STANDBY, Spirit1State.STANDBY)

    def lock_tx(self) -> bool:
        return self._change_state(Spirit1Commands.LOCKTX, Spirit1State.LOCK)

    def lock_rx(self) -> bool:
        return self._change_state(Spirit1Commands.LOCKRX, Spirit1State.LOCK)

    def ready(self) -> bool:
        return self._change_state(Spirit1Commands.READY, Spirit1State.READY)

    def sleep(self) -> bool:
        """Enter the low-power sleep state without losing configuration."""
        return self._change_state(Spirit1Commands.SLEEP, Spirit1State.SLEEP)

    def flush_rx_fifo(self) -> bool:
        return self._change_state(Spirit1Commands.FLUSHRXFIFO, Spirit1State.READY)

    def flush_tx_fifo(self) -> bool:
        return self._change_state(Spirit1Commands.FLUSHTXFIFO, Spirit1State.READY)

    def start_rx(self) -> bool:
        return self._change_state(Spirit1Commands.RX, Spirit1State.RX)

    def start_tx(self) -> bool:
        return self._change_state(Spirit1Commands.TX, Spirit1State.TX)

    def sabort(self) -> bool:
        return self._change_state(Spirit1Commands.SABORT, Spirit1State.READY)

    def refresh_status(self) -> bool:
        _ = self._spi_xfer(0x01, 0xC0, 0xC1)
        return self.status.is_valid

    # SPI I/O
    def read_register(self, register: Register) -> int:
        """Read and return the value of one register."""
        return self.read_register_block(register, 1)[0]

    def read_register_block(self, start: Register, count: int) -> bytearray:
        """Read a consecutive register block in one SPI transaction."""
        if count < 0:
            raise ValueError("Register block size must not be negative")
        start_address = start.value if isinstance(start, Spirit1Registers) else start
        regs: tuple[int, ...] = (0x01, start_address) + tuple(0x0 for _ in range(count))
        return self._spi_xfer(*regs)

    def write_registers(self, start_register: Register, *args: int) -> bytearray:
        start_address = start_register.value if isinstance(start_register, Spirit1Registers) else start_register
        regs = [0x00, start_address] + list(args)
        vals = self._spi_xfer(*regs)
        return vals

    def send_command(self, cmd:Spirit1Commands):
        if not 0x5F < cmd.value < 0x73 and cmd.value not in [0x6E, 0x6F]:
            logger.error(f"Invalid command: {cmd.value:02x}. Must be between 0x60 and 0x72, but not 0x6E or 0x6F.")
            return
        _ = self._spi_xfer(0x80, cmd.value)

    def get_register_bit(self, register: Register, bit: int) -> bool:
        return (self.read_register(register) & (1 << bit)) == (1 << bit)

    def set_register_bit(self, register: Register, bit: int, onoff: bool) -> None:
        value = self.read_register(register)
        value = (value & (0xFF - (1 << bit))) + (onoff << bit)
        _ = self.write_registers(register, value)

    def update_register(self, register: Register, mask: int, add: int) -> None:
        val = self.read_register(register)
        val = (val & mask) + add
        _ = self.write_registers(register, val)

    # Linear FIFO access
    def read_linear_fifo(self, nbytes:int) -> bytearray:
        if nbytes == 0:
            logger.warning("read_fifo() for 0 bytes?")
            return bytearray()
        regs = [0x01, 0xff] + [0xff for n in range(nbytes)]
        return self._spi_xfer(*regs)

    def write_linear_fifo(self, data:AnyStr) -> bytearray:
        regs = [0x0, 0xFF]
        for a in data:
            regs.append(a if isinstance(a, int) else ord(a))
        return self._spi_xfer(*regs)

    def linear_fifo_rx_size(self) -> int:
        return self.read_register(Spirit1Registers.LINEAR_FIFO_STATUS_0) & 0x7F

    def linear_fifo_tx_size(self) -> int:
        return self.read_register(Spirit1Registers.LINEAR_FIFO_STATUS_1) & 0x7F

    # Internal functions...
    def _spi_xfer(self, *args:int) -> bytearray:
        if self.is_closed:
            logger.warning("Device is closed.")
            return bytearray()
        if self.debug_spi or (args[0] == 0x00 and self.debug_spi_tx):
            wr = "SPI >>> " + " ".join([f"{x:02x}" for x in args])
            logger.debug(wr)
        vals = bytearray(self._spi.xfer2(args))
        if self.debug_spi:
            rc = "SPI <<< " + " ".join([f"{x:02x}" for x in vals])
            logger.debug(rc)
        _ = self.status.update(vals)
        return bytearray(vals[2:])


    def _change_state(self, cmd: Spirit1Commands, new_state: Spirit1State) -> bool:
        if self.status.state == Spirit1State.LOCKWON and cmd != Spirit1Commands.SRES:
                logger.warning(
                    "Device reported LOCKWON while changing to %s; resetting before retrying",
                    new_state.name,
                )
                if not self.reset():
                    logger.error("Unable to recover the device from LOCKWON")
                    return False

        self.send_command(cmd)

        deadline = time.monotonic() + 0.1  # 100 ms
        while self.status.state != new_state:
            if time.monotonic() >= deadline:
                logger.error(
                    "Unable to change state. Presently in %s but wanted %s",
                    self.status.state.name,
                    new_state.name,
                )
                return False

            time.sleep(0.001)  # 1 ms
            _ = self.refresh_status()

        return True

    def _require_sdn(self) -> ShutdownPin:
        if self._sdn is None:
            raise RuntimeError("SDN control is not configured for this device")
        return self._sdn

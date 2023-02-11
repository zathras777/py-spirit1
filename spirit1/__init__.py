import logging

from typing import Any, AnyStr, List

from .status import Spirit1Status
from .constants import Spirit1Commands, Spirit1State
from .registers import Spirit1Registers


logger = logging.getLogger(__name__)


class Spirit1:
    def __init__(self, spi:Any):
        self._spi = spi
        self.is_shutdown:bool = False
        self.debug_spi:bool = False
        self.debug_spi_tx:bool = False
        self.status:Spirit1State = Spirit1Status()

        self.refresh_status()
        if self.status.state == Spirit1State.LOCKWON:
            self.reset()

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

    def refresh_status(self):
        self._spi_xfer(0x01, 0xC0, 0xC1)

    # SPI I/O
    def read_registers(self, *args:Spirit1Registers) -> bytearray:
        regs:tuple[int] = (0x01,) + tuple(a.value for a in args) + (0x00,)
        return self._spi_xfer(*regs)

    def write_registers(self, start_register:Spirit1Registers, *args:int) -> bytearray:
        regs = [0x00, start_register.value] + list(args)
        vals = self._spi_xfer(*regs)
        return vals

    def send_command(self, cmd:Spirit1Commands):
        if not 0x5F < cmd.value < 0x73 and cmd.value not in [0x6E, 0x6F]:
            logger.error(f"Invalid command: {cmd.value:02x}. Must be between 0x60 and 0x72, but not 0x6E or 0x6F.")
            return
        self._spi_xfer(0x80, cmd.value)

    def get_register_bit(self, register:int, bit:int) -> bool:
        vals = self.read_registers(register)
        return (vals[0] & (1 << bit)) == (1 << bit)

    def set_register_bit(self, register:int, bit:int, onoff:bool):
        vals = self.read_registers(register)
        vals[0] = (vals[0] & (0xFF - (1 << bit))) + (onoff << bit)
        self.write_registers(register, vals[0])

    def update_register(self, register:Spirit1Registers, mask:int, add:int):
        val = self.read_registers(register)[0]
        val = (val & mask) + add
        self.write_registers(register, val)

    # Linear FIFO access
    def read_linear_fifo(self, nbytes:int) -> bytearray:
        if nbytes == 0:
            logger.warning("read_fifo() for 0 bytes?")
            return bytearray()
        regs = [0x01, 0xff] + [0xff for n in range(nbytes)]
        return self._spi_xfer(*regs)

    def write_linear_fifo(self, data:AnyStr) -> bytearray:
        regs = [0x0, 0xFF] + [ord(a) for a in data]
        return self._spi_xfer(*regs)

    def linear_fifo_rx_size(self) -> int:
        return self.read_registers(Spirit1Registers.LINEAR_FIFO_STATUS_0)[0] & 0x7F

    # Internal functions...
    def _spi_xfer(self, *args:int) -> bytearray:
        if self.is_shutdown:
            logger.warning("Device is shutdown. Call enable() to activate.")
            return bytearray()
        if self.debug_spi or (args[0] == 0x00 and self.debug_spi_tx):
            wr = "SPI >>> " + " ".join([f"{x:02x}" for x in args])
            logger.debug(wr)
        vals = self._spi.xfer2(args)
        if self.debug_spi:
            rc = "SPI <<< " + " ".join([f"{x:02x}" for x in vals])
            logger.debug(rc)
        self.status.update(vals)
        return bytearray(vals[2:])

    def _change_state(self, cmd:int, new_state:Spirit1State)-> bool:
        if not cmd in Spirit1Commands:
            logger.warning("Unable to change state using command %02x as it's not in the command list?", cmd)
            return False
        self.send_command(cmd)
        cycles:int = 0
        while self.status.state != new_state:
            cycles += 1
            self.refresh_status()
            if cycles >= 20:
                logger.error("Unable to change state. Presently in %s but wanted %s", self.status.state.name, new_state.name)
                return False
        
        return True

import logging

from typing import Any, Optional

from . import Spirit1
from .irq import SpiritIrq, debug_irq_status, IRQ
from .registers import Spirit1Registers


logger = logging.getLogger(__name__)

class ReceivedMessage:
    def __init__(self, payload:Optional[bytearray]=None):
        self.payload:Optional[bytearray] = payload
        self.rssi:Optional[int] = None
        self.sqi:Optional[int] = None
        self.pqi:Optional[int] = None
        self.agc_word:Optional[int] = None

    def update_quality(self, spirit:Spirit1):
        vals = spirit.read_n_registers(Spirit1Registers.LINK_QUALIF_2, 3)
        self.sqi = vals[1] & 0x7F
        self.pqi = vals[0] & 0x7F
        self.agc_word = vals[2] & 0x0F  
        self.rssi = spirit.read_registers(Spirit1Registers.RSSI_LEVEL)[0]


class Receiver:
    def __init__(self, spirit:Spirit1, irq:IRQ):
        self.spirit = spirit
        self.irq = irq
        self.should_run:bool = True
        self.debug:bool = False
        self.log_times:bool = False
        self.buffers:list[bytearray] = []
        self.buffer_limit:int = 0
        self.callback = None

    def get_persistent_rx(self) -> bool:
        return self.spirit.get_register_bit(Spirit1Registers.PROTOCOL_0, 1)

    def set_persistent_rx(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_0, 1, onoff)

    def stop(self):
        self.should_run = False
        self.spirit.sabort()

    async def receive(self) -> Any:
        buffer = bytearray()

        if not self.spirit.flush_rx_fifo():
            logger.error("Unable to flush the RX FIFO.")
            yield False
        if not self.spirit.start_rx():
            logger.error("Unable to enter the RX state.")
            yield False

        while self.should_run:
            status = self.irq.get_status()

            if self.debug and status != 0 and status != SpiritIrq.RSSI_ABOVE_TH.value:
                debug_irq_status(status)

            if IRQ.check_flag(status, SpiritIrq.RX_FIFO_ALMOST_FULL):
                fifo_sz = self.spirit.linear_fifo_rx_size()
                if fifo_sz > 0:
                    buffer += self.spirit.read_linear_fifo(fifo_sz)
            if IRQ.check_flag(status, SpiritIrq.RX_TIMEOUT):
                logger.info("RX_TIMEOUT received")
                break
            if IRQ.check_flag(status, SpiritIrq.RX_DATA_READY):
                fifo_sz = self.spirit.linear_fifo_rx_size()
                if fifo_sz > 0:
                    buffer += self.spirit.read_linear_fifo(fifo_sz)

                rcd = ReceivedMessage(buffer)
                rcd.update_quality(self.spirit)
                if self.callback:
                    yield(self.callback(rcd))
                else:
                    yield(rcd)
                                
                buffer = bytearray()
                self.spirit.sabort()
                self.spirit.flush_rx_fifo()
                self.spirit.start_rx()

        if self.should_run:
            # Exit the RX state if not called via stop()
            self.spirit.sabort()
        yield True

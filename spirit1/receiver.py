import logging

from . import Spirit1
from .irq import SpiritIrq, debug_irq_status, IRQ
from .registers import Spirit1Registers


logger = logging.getLogger(__name__)

class Receiver:
    def __init__(self, spirit:Spirit1, irq:IRQ):
        self.spirit = spirit
        self.irq = irq
        self.should_run:bool = True
        self.debug:bool = False
        self.log_times:bool = False
        self.buffers:list[bytearray] = []
        self.buffer_limit:int = 0

    def get_persistent_rx(self) -> bool:
        return self.spirit.get_register_bit(Spirit1Registers.PROTOCOL_0, 1)

    def set_persistent_rx(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_0, 1, onoff)

    def stop(self):
        self.should_run = False
        self.spirit.sabort()

    def receive(self) -> bool:
        buffer = bytearray()

        if not self.spirit.flush_rx_fifo():
            logger.error("Unable to flush the RX FIFO.")
            return False
        if not self.spirit.start_rx():
            logger.error("Unable to enter the RX state.")
            return False

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

                if self.debug:
                    mtxt = ""
                    for m in buffer:
                        mtxt += f"{m:02x} "
                    logger.debug(mtxt)
                if self.log_times:
                    sqi = self.spirit.read_registers(Spirit1Registers.LINK_QUALIF_1)[0] & 0x7F
                    rssi = self.spirit.read_registers(Spirit1Registers.RSSI_LEVEL)[0]
                    logger.debug("messsage of %d bytes, SQI %d, RSSI %d", len(buffer), sqi, rssi)
                
                self.buffers.append(buffer)
                if self.buffer_limit > 0 and len(self.buffers) >= self.buffer_limit:
                    logger.info("%d messages have been stored. Exiting receive loop.", len(self.buffers))
                    break
                
                buffer = bytearray()
                self.spirit.sabort()
                self.spirit.flush_rx_fifo()
                self.spirit.start_rx()

        if self.should_run:
            # Exit the RX state if not called via stop()
            self.spirit.sabort()
        if self.buffer_limit > 0 and len(self.buffers) != self.buffer_limit:
            logger.info("Unable to receive %d packets. Returning with %d available.", self.buffer_limit, len(self.buffers))
            return False
        return True

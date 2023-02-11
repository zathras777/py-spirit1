from enum import Enum

from . import Spirit1
from .registers import Spirit1Registers


class SpiritIrq(Enum):
    RX_DATA_READY = (1 << 0)        # RX data ready
    RX_DATA_DISC = (1 << 1)         # RX data discarded (upon filtering)
    TX_DATA_SENT = (1 << 2)         # TX data sent
    MAX_RE_TX_REACH = (1 << 3)      # Max re-TX reached
    CRC_ERROR = (1 << 4)            # CRC error
    TX_FIFO_ERROR = (1 << 5)        # TX FIFO underflow/overflow error
    RX_FIFO_ERROR = (1 << 6)        # RX FIFO underflow/overflow error
    TX_FIFO_ALMOST_FULL = (1 << 7)  # TX FIFO almost full

    TX_FIFO_ALMOST_EMPTY = (1 << 8) # TX FIFO almost empty
    RX_FIFO_ALMOST_FULL = (1 << 9)  # RX FIFO almost full
    RX_FIFO_ALMOST_EMPTY = (1 << 10) # RX FIFO almost empty 
    MAX_BO_CCA_REACH = (1 << 11)     # Max number of back-off during CCA
    VALID_PREAMBLE = (1 << 12)       # Valid preamble detected
    VALID_SYNC = (1 << 13)           # Sync word detected
    RSSI_ABOVE_TH = (1 << 14)        # RSSI above threshold
    WKUP_TOUT_LDC = (1 << 15)        # Wake-up timeout in LDC mode

    READY = (1 << 16)                # READY state
    STANDBY_DELAYED = (1 << 17)      # STANDBY state after MCU_CK_CONF_CLOCK_TAIL_X clock cycles
    LOW_BATT_LVL = (1 << 18)         # Battery level below threshold*/
    POR = (1 << 19)                  # Power On Reset
    BOR = (1 << 20)                  # Brown out event (both accurate and inaccurate)*/
    LOCK = (1 << 21)                 # LOCK state
    PM_COUNT_EXPIRED = (1 << 22)     # only for debug; Power Management startup timer expiration (see reg PM_START_COUNTER, 0xB5)
    XO_COUNT_EXPIRED = (1 << 23)     # only for debug; Crystal oscillator settling time counter expired


    SYNTH_LOCK_TIMEOUT = (1 << 24)   # only for debug; LOCK state timeout
    SYNTH_LOCK_STARTUP = (1 << 25)   # only for debug; see CALIBR_START_COUNTER
    SYNTH_CAL_TIMEOUT = (1 << 26)    # only for debug; SYNTH calibration timeout
    TX_START_TIME = (1 << 27)        # only for debug; TX circuitry startup time; see TX_START_COUNTER
    RX_START_TIME = (1 << 28)        # only for debug; RX circuitry startup time; see TX_START_COUNTER
    RX_TIMEOUT = (1 << 29)           # RX operation timeout
    AES_END = (1 << 30)              # AES End of operation

class IRQ:
    def __init__(self, spirit:Spirit1):
        self.spirit = spirit
        self.mask:int = 0

    def init(self):
        self.spirit.write_registers(Spirit1Registers.IRQ_MASK_3, 0, 0, 0, 0)

    def enable_irq(self, irq:SpiritIrq, onoff:bool):
        self.mask &= (0xFFFFFFFF - irq.value)
        if onoff:
            self.mask += irq.value

    def write_irqs(self):
        irqvals = [(self.mask >> (8 * i)) & 0xff for i in range(4)]
        self.spirit.write_registers(Spirit1Registers.IRQ_MASK_3, *(reversed(irqvals)))

    def get_status(self) -> int:
        irqst = self.spirit.read_registers(Spirit1Registers.IRQ_STATUS_3,
                                           Spirit1Registers.IRQ_STATUS_2,
                                           Spirit1Registers.IRQ_STATUS_1,
                                           Spirit1Registers.IRQ_STATUS_0)
        return sum([(x << (8 * (3 - i))) for i, x in enumerate(irqst)])

    @classmethod
    def check_flag(cls, status:int, flag:SpiritIrq) -> bool:
        return status & flag.value == flag.value

    def irq_clear_status(self):
        irqst = self.spirit.read_registers(Spirit1Registers.IRQ_STATUS_3,
                                           Spirit1Registers.IRQ_STATUS_2,
                                           Spirit1Registers.IRQ_STATUS_1,
                                           Spirit1Registers.IRQ_STATUS_0)
        print(f"{irqst[0]:02x} {irqst[1]:02x} {irqst[2]:02x} {irqst[3]:02x}")

    def irq_check_flag(self, flag:SpiritIrq) -> bool:
        irqst = self.spirit.read_registers(Spirit1Registers.IRQ_STATUS_3,
                                           Spirit1Registers.IRQ_STATUS_2,
                                           Spirit1Registers.IRQ_STATUS_1,
                                           Spirit1Registers.IRQ_STATUS_0)
        val = sum([(x << (8 * (3 - i))) for i, x in enumerate(irqst)])
        return (val & flag.value) == flag

def debug_irq_status(sts:int):
    print(f"Status: {sts:032b}")
    for poss in list(SpiritIrq):
        if (sts & poss.value) == poss.value:
            print(f"  + {poss.name}")


"""
class IrqConfig:
    def __init__(self):

      SYNTH_LOCK_TIMEOUT = auto()   # only for debug; LOCK state timeout
    SYNTH_LOCK_STARTUP = auto()   # only for debug; see CALIBR_START_COUNTER
    SYNTH_CAL_TIMEOUT = auto()    # only for debug; SYNTH calibration timeout
    TX_START_TIME = auto()        # only for debug; TX circuitry startup time; see TX_START_COUNTER
    RX_START_TIME = auto()        # only for debug; RX circuitry startup time; see TX_START_COUNTER
    RX_TIMEOUT = auto()           # RX operation timeout
    AES_END = auto()              # AES End of operation
    reserved = auto()                 # Reserved bit

    READY = auto()                # READY state
    STANDBY_DELAYED = auto()      # STANDBY state after MCU_CK_CONF_CLOCK_TAIL_X clock cycles
    LOW_BATT_LVL = auto()         # Battery level below threshold*/
    POR = auto()                  # Power On Reset
    BOR = auto()                  # Brown out event (both accurate and inaccurate)*/
    LOCK = auto()                 # LOCK state
    PM_COUNT_EXPIRED = auto()     # only for debug; Power Management startup timer expiration (see reg PM_START_COUNTER, 0xB5)
    XO_COUNT_EXPIRED = auto()     # only for debug; Crystal oscillator settling time counter expired

    TX_FIFO_ALMOST_EMPTY = auto() # TX FIFO almost empty
    RX_FIFO_ALMOST_FULL = auto()  # RX FIFO almost full
    RX_FIFO_ALMOST_EMPTY = auto() # RX FIFO almost empty 
    MAX_BO_CCA_REACH = auto()     # Max number of back-off during CCA
    VALID_PREAMBLE = auto()       # Valid preamble detected
    VALID_SYNC = auto()           # Sync word detected
    RSSI_ABOVE_TH = auto()        # RSSI above threshold
    WKUP_TOUT_LDC = auto()        # Wake-up timeout in LDC mode

    RX_DATA_READY = auto()        # RX data ready
    RX_DATA_DISC = auto()         # RX data discarded (upon filtering)
    TX_DATA_SENT = auto()         # TX data sent
    MAX_RE_TX_REACH = auto()      # Max re-TX reached
    CRC_ERROR = auto()            # CRC error
    TX_FIFO_ERROR = auto()        # TX FIFO underflow/overflow error
    RX_FIFO_ERROR = auto()        # RX FIFO underflow/overflow error
    TX_FIFO_ALMOST_FULL = auto()  # TX FIFO almost full
"""
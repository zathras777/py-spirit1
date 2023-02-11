from .constants import Spirit1State


class Spirit1Status:
    def __init__(self):
        self.state:Spirit1State = Spirit1State.STANDBY
        self.xo_on:bool = False
        self.ant_select:bool = False
        self.error_lock:bool = False
        self.rx_fifo_empty:bool = False
        self.tx_fifo_full:bool = False

    def update(self, vals:bytearray):
        #self.state = vals[1] >> 1
        self.xo_on = (vals[1] & 0x01) == 0x01
        self.ant_select = (vals[0] & 0x08) == 0x08
        self.tx_fifo_full = (vals[0] & 0x04) == 0x04
        self.rx_fifo_empty = (vals[0] & 0x02) == 0x02
        self.error_lock = (vals[0] & 0x01) == 0x01
        for sts in list(Spirit1State):
            if sts.value == vals[1] >> 1:
                self.state = sts
                break
        
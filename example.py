import asyncio
import logging
import sys

from typing import List, Tuple

from spirit1 import Spirit1
from spirit1.basic_packet import BasicPacket, BasicPacketMessage
from spirit1.constants import CrcMode, Spirit1Modulation
from spirit1.receiver import Receiver
from spirit1.irq import IRQ, SpiritIrq
from spirit1.qi import QI
from spirit1.radio import Radio
from spirit1.timer import Timer

try:
    import spidev
    USE_SPIDEV = True
except ImportError:
    USE_SPIDEV = False

# This is a very basic class that allows me to run this script on the development machine and check for
# bugs in the code prior to copying it over to the RaspberryPi.
class TestSpi:
    def __init__(self):
        self.state = [0x52, 0x07]
        self.registers:List[int] = [
            0x0c, 0xc0, 0xa2, 0xa2, 0xa2, 0x0a, 0x00, 0xa3, 0x0c, 0x84, 0xec, 0x51, 0xfc, 0xa3, 0x00, 0x00, 
            0x03, 0x0e, 0x1a, 0x25, 0x35, 0x40, 0x4e, 0x00, 0x07, 0x00, 0x83, 0x1a, 0x45, 0x23, 0x48, 0x18, 
            0x25, 0xe3, 0x24, 0x58, 0x22, 0x62, 0x8a, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x07, 0x1e, 0x20, 0x00, 0x14, 0x88, 0x88, 0x88, 0x88, 0x02, 0x20, 0x20, 0x00, 0x30, 0x30, 
            0x30, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x70, 
            0x02, 0x00, 0x08, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x70, 0x48, 0x48, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x05, 0xe8, 0x37, 0x08, 0x08, 0xf7, 0x00, 0x00, 0x00, 0x5b, 0x20, 
            0x34, 0x11, 0xd6, 0x37, 0x0c, 0x20, 0x00, 0xe1, 0x00, 0x01, 0x02, 0x28, 0x05, 0x83, 0xf5, 0x00, 
            0x08, 0x00, 0x42, 0x00, 0x21, 0x10, 0xff, 0x00, 0x01, 0x00, 0x03, 0x03, 0x04, 0x00, 0x00, 0x00, 
            0x02, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0x70, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x01, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0d, 0x05, 0x00, 0x00, 0x00
        ]

    def xfer2(self, *vals:Tuple[int]) -> List[int]:
        rv = [self.registers[0xc0], self.registers[0xc1]]
        txfr:Tuple[int] = vals[0]
        if txfr[0] == 0x00:
            start_reg = txfr[1]
            for n, v in enumerate(txfr[2:]):
                self.registers[start_reg + n] = v
                rv.append(v)
        elif txfr[0] == 0x01:
            for n in txfr[1:-1]:
                rv.append(self.registers[n])
        elif txfr[0] == 0x80:
            if txfr[1] == 0x63:
                self.registers[0xC1] = 0x80
            elif txfr[1] == 0x62:
                self.registers[0xC1] = 0x07
            elif txfr[1] in [0x65, 0x66]:
                self.registers[0xC1] = 0x1F
            elif txfr[1] == 0x61:
                self.registers[0xC1] = 0x67
            return self.state
        return rv

log_format = "%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s"
date_format = "%H:%M:%S"
logging.basicConfig(stream=sys.stdout, 
                    level=logging.DEBUG,
                    format=log_format, 
                    datefmt=date_format)

logger = logging.getLogger(__name__)


async def main():
    pkt_count = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    if USE_SPIDEV:
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 250000
        spi.mode = 0b00

    else:
        spi = TestSpi()

    spirit = Spirit1(spi)
    spirit.reset()
    radio = Radio(spirit)

    radio.set_xtal_frequency(int(50e6))
    radio.set_datarate(50000)
    radio.set_modulation_scheme(Spirit1Modulation.GFSK_BT05)
    radio.init_device()
    radio.set_frequency_base(int(868.2e6))

    pkt = BasicPacket(spirit)
    pkt.preamble_length = 5
    pkt.sync_length = 4
    pkt.sync_words = [0x5a, 0x47, 0x52, 0x50]
    pkt.fixed_length = False
    pkt.fixed_packet_length = 100
    pkt.crc_mode = CrcMode.CRC_MODE_864CBF
    pkt.control_length = 4
    pkt.address_field = True
    pkt.fec = True
    pkt.data_whitening = True
    pkt.init()

    irq = IRQ(spirit)
    irq.init()
    irq.enable_irq(SpiritIrq.RX_DATA_READY, True)
    irq.enable_irq(SpiritIrq.RX_TIMEOUT, True)
    irq.write_irqs()

    qi = QI(spirit)
    qi.sqi_set_threshold(0)
    qi.sqi_enable(True)
    qi.pqi_set_threshold(0)
    qi.pqi_enable(True)

    timer = Timer(spirit, int(50e6))
    timer.set_rx_timeout_stop_conditions()
    timer.set_rx_timeout_counter(0)

    radio.set_pa_level_dbm(0, 11.6)
    radio.set_pa_level_max_index(0)

    rcvr = Receiver(spirit, irq)
    rcvr.log_times = True
    rcvr.set_persistent_rx(True)
    rcvr.buffer_limit = pkt_count
    rcvr.callback = pkt.get_message

    print(f"Trying to receive {pkt_count} messages.")
    received:int = 0

    async for nxt in rcvr.receive():
        if nxt in [True, False]:
            break

        print(nxt.one_line())
        print(f"    {{'address': 0x{nxt.address:02x}, 'control': [{nxt.ctrl_str()}], 'payload': [{nxt.payload_str()}]}},")

        received += 1
        if received >= pkt_count:
            break


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.stop()
        pass

import asyncio
import logging
import sys

from spirit1 import RadioConfig, Spirit1Device, format_basic_packet
from spirit1.basic_packet import BasicPacket, BasicPacketConfig
from spirit1.enums import CrcMode, Spirit1Modulation
from spirit1.irq import IRQ, IRQConfig, SpiritIrq
from spirit1.qi import QI, QIConfig
from spirit1.radio import Radio
from spirit1.receiver import Receiver
from spirit1.timer import Timer, TimerConfig

try:
    import spidev
except ImportError as error:
    raise RuntimeError("This example requires the optional 'spidev' dependency") from error


logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    packet_count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 250_000
    spi.mode = 0b00

    spirit = Spirit1Device(spi)
    spirit.reset()
    radio = Radio(spirit, RadioConfig(
        xtal_frequency=50_000_000,
        datarate=50_000,
        modulation=Spirit1Modulation.GFSK_BT05,
        base_frequency=868_200_000,
    ))
    radio.init_device()

    packet = BasicPacket(spirit, BasicPacketConfig(
        preamble_length=5,
        sync_words=(0x5A, 0x47, 0x52, 0x50),
        fixed_packet_length=100,
        crc_mode=CrcMode.CRC_MODE_864CBF,
        control_length=4,
        address_field=True,
        fec=True,
        data_whitening=True,
    ))
    packet.apply()

    irq = IRQ(spirit, IRQConfig({SpiritIrq.RX_DATA_READY, SpiritIrq.CRC_ERROR, SpiritIrq.RX_TIMEOUT}))
    irq.apply()
    QI(spirit, QIConfig(sqi_enabled=True, pqi_enabled=True)).apply()
    Timer(spirit, TimerConfig(xtal_frequency=radio.config.xtal_frequency)).apply()

    radio.set_pa_level_dbm(0, 11.6)
    radio.set_pa_level_max_index(0)

    receiver = Receiver(spirit, irq)
    receiver.set_persistent_rx(True)

    print(f"Trying to receive {packet_count} messages.")
    received = 0
    try:
        async for message in packet.receive(receiver):
            print(format_basic_packet(message))
            received += 1
            if received >= packet_count:
                break
    finally:
        receiver.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

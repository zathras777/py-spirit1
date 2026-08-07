"""Capture raw SPIRIT1 receiver messages as newline-delimited JSON.

The output is suitable for saving as a fixture.  It includes the raw RX FIFO
payload and the packet fields SPIRIT1 exposes through receive-status registers.
The radio and packet settings intentionally match ``example.py``.
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone

from spirit1 import BasicPacket, BasicPacketConfig, RadioConfig, Spirit1Device
from spirit1.enums import CrcMode, Spirit1Modulation
from spirit1.irq import IRQ, IRQConfig, SpiritIrq
from spirit1.qi import QI, QIConfig
from spirit1.radio import Radio
from spirit1.receiver import Receiver
from spirit1.timer import Timer, TimerConfig


def message_record(raw_message, packet_message) -> dict:
    """Return raw FIFO bytes and packet-status fields as a JSON record."""
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "payload": bytes(raw_message.payload).hex(),
        "crc_valid": raw_message.crc_valid,
        "rssi": raw_message.rssi,
        "sqi": raw_message.sqi,
        "pqi": raw_message.pqi,
        "agc_word": raw_message.agc_word,
        "source_address": packet_message.source_address,
        "destination_address": packet_message.destination_address,
        "control_data": packet_message.control_data.hex(),
        "crc": packet_message.crc.hex() if packet_message.crc is not None else None,
    }


async def capture(args: argparse.Namespace) -> None:
    try:
        import spidev
    except ImportError as error:
        raise SystemExit("This utility requires the optional 'spidev' dependency") from error

    spi = spidev.SpiDev()
    spi.open(args.bus, args.device)
    spi.max_speed_hz = args.speed
    spi.mode = 0b00

    try:
        spirit = Spirit1Device(spi)
        spirit.reset()
        radio = Radio(spirit, RadioConfig(
            xtal_frequency=50_000_000,
            datarate=50_000,
            modulation=Spirit1Modulation.GFSK_BT05,
            base_frequency=868_200_000,
        ))
        if not radio.init_device():
            raise RuntimeError("Unable to initialise the radio")

        # This config must match the transmitter whose messages are captured.
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

        receiver = Receiver(spirit, irq, ignore_invalid_crc=not args.include_invalid_crc)
        receiver.set_persistent_rx(True)
        captured = 0
        try:
            async for message in receiver.receive():
                # Addresses, control bytes, and CRC are status registers, so
                # read them before the receiver restarts RX for the next frame.
                print(json.dumps(message_record(message, packet.decode(message))), flush=True)
                captured += 1
                if args.count and captured >= args.count:
                    break
        finally:
            receiver.stop()
    finally:
        spi.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus", type=int, default=0, help="SPI bus number (default: 0)")
    parser.add_argument("--device", type=int, default=0, help="SPI device number (default: 0)")
    parser.add_argument("--speed", type=int, default=250_000, help="SPI speed in Hz")
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Stop after this many messages; 0 captures until interrupted (default: 0)",
    )
    parser.add_argument(
        "--include-invalid-crc",
        action="store_true",
        help="Record messages for which SPIRIT1 reports CRC_ERROR",
    )
    args = parser.parse_args()
    if args.count < 0:
        parser.error("--count must not be negative")
    asyncio.run(capture(args))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

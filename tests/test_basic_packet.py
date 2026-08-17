import asyncio
import unittest

from spirit1.basic_packet import BasicPacket, BasicPacketConfig, BasicPacketMessage
from spirit1.enums import CrcMode
from spirit1.formatting import (
    basic_packet_to_dict,
    format_basic_packet,
    format_basic_packet_one_line,
    to_dict,
)
from spirit1.receiver import ReceivedMessage
from spirit1.registers import Spirit1Registers


class PacketDevice:
    def __init__(self):
        self.writes = []

    def set_register_bit(self, *values):
        self.writes.append(("bit", values))

    def read_register(self, register):
        return 0x00

    def read_register_block(self, register, length):
        values = {
            Spirit1Registers.RX_ADDRESS_1: bytearray([0x24, 0x42]),
            Spirit1Registers.RX_CTRL_FIELD_1: bytearray([0xA1, 0xB2]),
            Spirit1Registers.CRC_FIELD_1: bytearray([0x12, 0x34]),
        }
        return values.get(register, bytearray(length))

    def write_registers(self, register, *values):
        self.writes.append(("write", register, values))

    def flush_tx_fifo(self):
        self.writes.append(("flush_tx_fifo",))
        return True

    def write_linear_fifo(self, payload):
        self.writes.append(("write_linear_fifo", bytes(payload)))

    def start_tx(self):
        self.writes.append(("start_tx",))
        return True

    def linear_fifo_tx_size(self):
        return 0


class RawSource:
    async def receive(self):
        yield ReceivedMessage(bytearray([0x01, 0x02]))


class BasicPacketTests(unittest.TestCase):
    def test_message_formats_empty_payload_safely(self):
        message = BasicPacketMessage(payload=b"")

        self.assertEqual(
            repr(message),
            "BasicPacketMessage(payload=b'', source_address=None, destination_address=None, "
            "control_data=b'', crc=None, raw=None)",
        )
        self.assertIn("Payload: \n", format_basic_packet(message))
        self.assertEqual(format_basic_packet_one_line(message), "")

    def test_packet_dictionary_is_json_friendly(self):
        message = BasicPacketMessage(
            payload=b"\x01\x02",
            source_address=0x24,
            destination_address=0x42,
            control_data=b"\xA0",
            crc=b"\x10",
        )

        self.assertEqual(
            basic_packet_to_dict(message),
            {
                "source_address": 0x24,
                "destination_address": 0x42,
                "control_data": [0xA0],
                "payload": [0x01, 0x02],
                "crc": [0x10],
                "crc_valid": None,
                "rssi": None,
                "sqi": None,
                "pqi": None,
                "agc_word": None,
            },
        )
        self.assertEqual(to_dict(message)["payload"], [0x01, 0x02])

    def test_config_reports_invalid_values_without_device_access(self):
        config = BasicPacketConfig(preamble_length=0, sync_words=(), control_length=5)

        self.assertEqual(len(config.validate()), 3)

    def test_apply_writes_the_configured_packet_registers(self):
        device = PacketDevice()
        config = BasicPacketConfig(
            preamble_length=5,
            sync_words=(0x5A, 0x47),
            control_length=2,
            address_field=True,
            crc_mode=CrcMode.CRC_MODE_1021,
        )

        self.assertTrue(BasicPacket(device, config).apply())

        self.assertEqual(device.writes[-2][2], (0x0A, 0x0F, 0x2B, 0x60))
        self.assertEqual(device.writes[-1][2], (0x47, 0x5A))

    def test_decode_returns_a_basic_packet_message_with_raw_metadata(self):
        device = PacketDevice()
        config = BasicPacketConfig(
            address_field=True,
            control_length=2,
            crc_mode=CrcMode.CRC_MODE_1021,
        )
        raw = ReceivedMessage(
            bytearray([0x10, 0x20]),
            crc_valid=True,
            rssi=99,
            sqi=10,
            pqi=4,
            agc_word=3,
            source_address=0x24,
            destination_address=0x42,
            control_data=b"\x00\x00\xA1\xB2",
            crc=b"\x34\x12\x00",
        )

        message = BasicPacket(device, config).decode(raw)

        self.assertEqual(message.payload, b"\x10\x20")
        self.assertEqual(message.source_address, 0x24)
        self.assertEqual(message.destination_address, 0x42)
        self.assertEqual(message.control_data, b"\xA1\xB2")
        self.assertEqual(message.crc, b"\x34\x12")
        self.assertTrue(message.crc_valid)
        self.assertIs(message.raw, raw)
        self.assertEqual(message.rssi, 99)

    def test_receive_converts_a_raw_stream_to_basic_packet_messages(self):
        packet = BasicPacket(spirit=None)

        async def collect_payloads():
            return [message.payload async for message in packet.receive(RawSource())]

        self.assertEqual(asyncio.run(collect_payloads()), [b"\x01\x02"])

    def test_transmit_sets_total_packet_length_for_variable_packets(self):
        device = PacketDevice()
        packet = BasicPacket(device, BasicPacketConfig(address_field=True, control_length=4))

        self.assertTrue(packet.transmit(BasicPacketMessage(
            payload=b"\x04",
            destination_address=0x00,
            source_address=0x00,
            control_data=b"\xC6\x01\x00\x00",
        )))

        self.assertIn(
            ("write", Spirit1Registers.PKTLEN_1, (0x00, 0x07)),
            device.writes,
        )

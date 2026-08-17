import unittest

from spirit1.enums import CrcMode
from spirit1.receiver import ReceivedMessage
from spirit1.stack_packet import (
    ExperimentalStackPacketWarning,
    StackPacket,
    StackPacketConfig,
)


class StackDevice:
    def __init__(self):
        self.calls = []

    def set_register_bit(self, *values):
        self.calls.append(("bit", values))

    def read_register(self, register):
        return 0

    def write_registers(self, register, *values):
        self.calls.append(("write", register, values))


class StackPacketTests(unittest.TestCase):
    def test_apply_selects_stack_format_and_warns(self):
        device = StackDevice()
        packet = StackPacket(device, StackPacketConfig(
            preamble_length=5,
            sync_words=(0x5A, 0x47),
            length_width=8,
            control_length=2,
            crc_mode=CrcMode.CRC_MODE_1021,
            no_ack=True,
        ))

        with self.assertWarns(ExperimentalStackPacketWarning):
            self.assertTrue(packet.apply())

        self.assertEqual(device.calls[2][2], (0x12, 0xC7, 0x2B, 0x60))
        self.assertEqual(device.calls[-2], ("bit", (0x50, 3, True)))
        self.assertEqual(device.calls[-1], ("bit", (0x50, 2, False)))

    def test_decode_uses_the_received_snapshot(self):
        raw = ReceivedMessage(
            payload=bytearray([0x10]),
            source_address=0x24,
            destination_address=0x42,
            control_data=b"\x00\x00\xA1\xB2",
            crc=b"\x34\x12\x00",
        )
        packet = StackPacket(None, StackPacketConfig(control_length=2, crc_mode=CrcMode.CRC_MODE_1021))

        message = packet.decode(raw)

        self.assertEqual(message.source_address, 0x24)
        self.assertEqual(message.destination_address, 0x42)
        self.assertEqual(message.control_data, b"\xA1\xB2")
        self.assertEqual(message.crc, b"\x34\x12")

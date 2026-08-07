import asyncio
import unittest

from spirit1.irq import SpiritIrq
from spirit1.receiver import Receiver
from spirit1.registers import Spirit1Registers


class ReceiverDevice:
    def __init__(self):
        self.aborts = 0

    def flush_rx_fifo(self):
        return True

    def start_rx(self):
        return True

    def sabort(self):
        self.aborts += 1

    def linear_fifo_rx_size(self):
        return 2

    def read_linear_fifo(self, size):
        return bytearray([0x12, 0x34])

    def read_register_block(self, register, count):
        if register == Spirit1Registers.LINK_QUALIF_2:
            return bytearray([0x04, 0x05, 0x06])
        self.assert_register(register, Spirit1Registers.CRC_FIELD_2)
        return bytearray([0x30, 0x20, 0x10, 0x01, 0x02, 0x03, 0x04, 0x24, 0x42])

    def read_register(self, register):
        self.assert_register(register, Spirit1Registers.RSSI_LEVEL)
        return 0x70

    @staticmethod
    def assert_register(actual, expected):
        if actual != expected:
            raise AssertionError(f"Expected register {expected:#x}, got {actual:#x}")


class ReceiverIrq:
    def __init__(self):
        self.statuses = [
            SpiritIrq.RX_DATA_READY.value | SpiritIrq.CRC_ERROR.value,
            SpiritIrq.RX_TIMEOUT.value,
        ]

    def get_status(self):
        return self.statuses.pop(0)


class ReceiverTests(unittest.TestCase):
    @staticmethod
    async def collect(ignore_invalid_crc):
        receiver = Receiver(
            ReceiverDevice(),
            ReceiverIrq(),
            poll_interval=0,
            ignore_invalid_crc=ignore_invalid_crc,
        )
        return [message async for message in receiver.receive()]

    def test_invalid_crc_messages_are_ignored_by_default(self):
        self.assertEqual(asyncio.run(self.collect(ignore_invalid_crc=True)), [])

    def test_invalid_crc_messages_can_be_returned_for_diagnostics(self):
        messages = asyncio.run(self.collect(ignore_invalid_crc=False))

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, bytearray([0x12, 0x34]))
        self.assertFalse(messages[0].crc_valid)
        self.assertEqual(messages[0].rssi, 0x70)
        self.assertEqual(messages[0].source_address, 0x24)
        self.assertEqual(messages[0].destination_address, 0x42)
        self.assertEqual(messages[0].control_data, b"\x01\x02\x03\x04")
        self.assertEqual(messages[0].crc, b"\x10\x20\x30")

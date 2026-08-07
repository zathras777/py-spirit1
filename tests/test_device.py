import unittest
from typing import Sequence

from spirit1 import Spirit1Device
from spirit1.enums import Spirit1Commands, Spirit1State
from spirit1.status import Spirit1Status


class FakeSpi:
    def __init__(self):
        self.transfers = []

    def xfer2(self, values: Sequence[int]) -> list[int]:
        self.transfers.append(tuple(values))
        return [0x00, 0x07] + [0x00] * (len(values) - 2)


class Spirit1DeviceTests(unittest.TestCase):
    def test_device_accepts_an_spi_compatible_transport(self):
        spi = FakeSpi()
        device = Spirit1Device(spi)

        value = device.read_register(0xC8)

        self.assertEqual(value, 0x00)
        self.assertEqual(spi.transfers[-1], (0x01, 0xC8, 0x00))

    def test_device_reads_consecutive_registers_as_one_block(self):
        spi = FakeSpi()
        device = Spirit1Device(spi)

        device.read_register_block(0xD2, 2)

        self.assertEqual(spi.transfers[-1], (0x01, 0xD2, 0x00, 0x00))

    def test_state_transition_resets_lockwon_before_retrying(self):
        device = object.__new__(Spirit1Device)
        device.status = Spirit1Status()
        device.status.state = Spirit1State.LOCKWON
        resets = []
        commands = []

        def reset():
            resets.append(True)
            device.status.state = Spirit1State.READY
            return True

        def send_command(command):
            commands.append(command)
            device.status.state = Spirit1State.RX

        device.reset = reset
        device.send_command = send_command
        device.refresh_status = lambda: None

        self.assertTrue(device._change_state(Spirit1Commands.RX, Spirit1State.RX))
        self.assertEqual(resets, [True])
        self.assertEqual(commands, [Spirit1Commands.RX])

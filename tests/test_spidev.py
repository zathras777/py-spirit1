import sys
import types
import unittest
from unittest.mock import patch

from spirit1.spidev import open_spidev


class FakeSpi:
    def __init__(self):
        self.opened = None
        self.closed = False
        self.max_speed_hz = None
        self.mode = None

    def open(self, bus, device):
        self.opened = (bus, device)

    def close(self):
        self.closed = True

    def xfer2(self, values):
        return [0, 0, *values[2:]]


class SpidevTests(unittest.TestCase):
    def test_open_spidev_configures_and_closes_the_transport(self):
        spi = FakeSpi()
        fake_module = types.SimpleNamespace(SpiDev=lambda: spi)

        with patch.dict(sys.modules, {"spidev": fake_module}):
            spirit = open_spidev(bus=1, device=2, speed_hz=500_000, mode=3)

        self.assertEqual(spi.opened, (1, 2))
        self.assertEqual(spi.max_speed_hz, 500_000)
        self.assertEqual(spi.mode, 3)
        spirit.close()
        self.assertTrue(spi.closed)

    def test_open_spidev_validates_arguments_before_importing_spidev(self):
        with self.assertRaises(ValueError):
            open_spidev(bus=-1)


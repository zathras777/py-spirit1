import sys
import types
import unittest
from unittest.mock import patch

from spirit1.gpio import open_gpiozero_sdn


class FakeOutputDevice:
    def __init__(self, pin, *, active_high, initial_value):
        self.pin = pin
        self.active_high = active_high
        self.value = initial_value
        self.closed = False

    def close(self):
        self.closed = True


class GpioTests(unittest.TestCase):
    def test_gpiozero_sdn_uses_bcm_gpio4_and_preserves_state_by_default(self):
        output = None

        def output_device(*args, **kwargs):
            nonlocal output
            output = FakeOutputDevice(*args, **kwargs)
            return output

        with patch.dict(sys.modules, {"gpiozero": types.SimpleNamespace(OutputDevice=output_device)}):
            sdn = open_gpiozero_sdn()

        self.assertEqual(output.pin, 4)
        self.assertTrue(output.active_high)
        self.assertIsNone(output.value)
        sdn.set_value(True)
        self.assertTrue(sdn.get_value())
        sdn.close()
        self.assertTrue(output.closed)

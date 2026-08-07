import unittest

from spirit1.radio import Radio
from spirit1.radio_config import RadioConfig


class RegisterDevice:
    def get_register_bit(self, register, bit):
        self.register = register
        self.bit = bit
        return True


class ReferenceDividerDevice:
    def __init__(self):
        self.writes = []

    def get_register_bit(self, register, bit):
        return False

    def set_register_bit(self, register, bit, value):
        self.writes.append((register, bit, value))


class CalibrationDevice:
    def write_registers(self, *args):
        pass

    def set_register_bit(self, *args):
        pass

    def refresh_status(self):
        pass

    def is_standby(self):
        return False

    def lock_tx(self):
        return True

    def lock_rx(self):
        return True

    def ready(self):
        return True

    def read_register(self, register):
        return 0x01


class RadioTests(unittest.TestCase):
    def test_get_agc_uses_the_public_device_register_method(self):
        device = RegisterDevice()
        radio = Radio(device)

        self.assertTrue(radio.get_agc())
        self.assertEqual(device.bit, 7)

    def test_vco_calibration_does_not_reenter_itself_while_restoring_divider(self):
        radio = Radio(
            CalibrationDevice(),
            RadioConfig(xtal_frequency=50_000_000, reference_divider=False),
        )
        writes = []
        radio.write_frequency_base = lambda do_calibration=True: writes.append(do_calibration)

        self.assertTrue(radio.vco_calibration())

        self.assertEqual(writes, [False, False])

    def test_unspecified_reference_divider_is_read_from_the_device(self):
        device = ReferenceDividerDevice()
        radio = Radio(device, RadioConfig())

        radio._configure_reference_divider()

        self.assertTrue(radio.reference_divider)
        self.assertEqual(device.writes, [])

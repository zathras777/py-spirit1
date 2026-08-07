import unittest

from spirit1.diagnostics import dump_configuration


class ConfigurationDevice:
    def read_register(self, register):
        return register.value


class DiagnosticsTests(unittest.TestCase):
    def test_configuration_dump_lists_stable_registers_in_address_order(self):
        output = dump_configuration(ConfigurationDevice())

        self.assertTrue(output.startswith("SPIRIT1 configuration:"))
        self.assertIn("0x01 ANA", output)
        self.assertIn("0xB4 XO_RCO_TEST", output)
        self.assertNotIn("RSSI_LEVEL", output)

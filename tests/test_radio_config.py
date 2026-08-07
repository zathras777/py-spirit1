import unittest

from spirit1 import RadioConfig
from spirit1.enums import Spirit1Modulation
from spirit1.radio import Radio


class RadioConfigTests(unittest.TestCase):
    def test_defaults_are_valid_and_serializable(self):
        config = RadioConfig()

        self.assertEqual(config.validate(), [])
        self.assertEqual(config.as_dict()["base_frequency"], 868_000_000)

    def test_invalid_values_are_reported_before_hardware_access(self):
        config = RadioConfig(
            base_frequency=600_000_000,
            datarate=0,
            freq_deviation=-1,
            bandwidth=0,
        )

        self.assertEqual(len(config.validate()), 4)

    def test_radio_uses_the_supplied_config_without_device_access(self):
        config = RadioConfig(
            base_frequency=433_920_000,
            datarate=38_400,
            modulation=Spirit1Modulation.FSK,
        )
        radio = Radio(spirit=None, config=config)

        self.assertIs(radio.config, config)
        self.assertEqual(radio.frequency_base.frequency, 433_920_000)
        self.assertEqual(radio.get_settings()["datarate"], 38_400)

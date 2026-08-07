import unittest

from spirit1.frequency import Frequency, FrequencyBand, VCOSetting


class FrequencyTests(unittest.TestCase):
    def test_high_band_frequency_generates_register_values(self):
        frequency = Frequency(868_200_000)

        self.assertTrue(frequency.is_possible())
        self.assertEqual(frequency.frequency_band, FrequencyBand.HIGH_BAND)
        self.assertIn(frequency.vco(), (VCOSetting.VCO_L, VCOSetting.VCO_H))
        self.assertEqual(len(frequency.synt_reg_values(False, 50_000_000)), 4)

    def test_out_of_band_frequency_is_rejected(self):
        self.assertFalse(Frequency(600_000_000).is_possible())

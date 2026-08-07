from enum import IntEnum
from typing import List


class FrequencyBand(IntEnum):
    HIGH_BAND     = 0x00   # High_Band selected: from 779 MHz to 915 MHz
    MIDDLE_BAND   = 0x01   # Middle Band selected: from 387 MHz to 470 MHz
    LOW_BAND      = 0x02   # Low Band selected: from 300 MHz to 348 MHz
    VERY_LOW_BAND = 0x03


class VCOSetting(IntEnum):
    VCO_L = 0x02
    VCO_H = 0x04

FBASE_DIVIDER   = 262144   # 2^18


class Frequency:
    def __init__(self, freq:int):
        self.frequency:int = freq
        self.frequency_band:FrequencyBand = self._frequency_band()

    def offset(self, offset:int):
        """ Return a new Frequenmcy object with the frequency offset from the current one. """
        return Frequency(self.frequency + offset)

    @classmethod
    def calculate(cls, synth_word:int, xtal:int, digital_divider:bool, band:int):
        """ Calculate the frequency from the supplied variables and return a new Frequency object. """
        factor = cls._band_factor(cls.frequency_band_from_reg(band)) / 2
        div_factor = int(digital_divider) + 1
        freq = round(synth_word * xtal / (FBASE_DIVIDER * div_factor * factor))
        return Frequency(freq)

    def is_possible(self) -> bool:
        """ Check the frequency supplied is valid for the SPIRIT1 bands. """
        if 778000000 <= self.frequency <= 957100000:
            return True
        if 386000000 <= self.frequency <= 471100000:  # 387-470 Mhz
            return True
        if 299000000 <= self.frequency <= 349100000:  # 300-348 Mhz
            return True
        if 149000000 <= self.frequency <= 175100000:  # 150-175 Mhz
            return True
        return False

    def vco(self) -> VCOSetting:
        """ Return the VCO. 
            Use vco().value to get a numeric value suitable for use in registers. 
        """
        if self.frequency_band == FrequencyBand.VERY_LOW_BAND:
            return VCOSetting.VCO_L if self.frequency < 161281250 else VCOSetting.VCO_H
        elif self.frequency_band == FrequencyBand.LOW_BAND:
            return VCOSetting.VCO_L if self.frequency < 322562500 else VCOSetting.VCO_H
        elif self.frequency_band == FrequencyBand.MIDDLE_BAND:
            return VCOSetting.VCO_L if self.frequency < 430083334 else VCOSetting.VCO_H
        elif self.frequency_band == FrequencyBand.HIGH_BAND:
            return VCOSetting.VCO_L if self.frequency < 860166667 else VCOSetting.VCO_H
        return VCOSetting.VCO_L

    def synth_word(self, digital_divider:bool, xtal:int) -> int:
        """ Calculate the synth word for the frequency. """
        div_factor = int(digital_divider) + 1
        return int(self.frequency * self.half_band_factor() * ((FBASE_DIVIDER * div_factor) / xtal))

    def band_factor(self) -> int:
        """ Supply the factor for the frequency band. """
        return Frequency._band_factor(self.frequency_band)

    def half_band_factor(self) -> int:
        """ Half the bad factor for the frequency band. """
        return int(self.band_factor() / 2)

    def band_reg_value(self) -> int:
        """ The value needed to be set for the frequency band. """
        if self.frequency_band == FrequencyBand.VERY_LOW_BAND:
            return 5
        elif self.frequency_band == FrequencyBand.LOW_BAND:
            return 4
        elif self.frequency_band == FrequencyBand.MIDDLE_BAND:
            return 3
        elif self.frequency_band == FrequencyBand.HIGH_BAND:
            return 1

    @classmethod
    def frequency_band_from_reg(cls, reg:int) -> FrequencyBand:
        if reg == 5:
            return FrequencyBand.VERY_LOW_BAND
        elif reg == 4:
            return FrequencyBand.LOW_BAND
        elif reg == 3:
            return FrequencyBand.MIDDLE_BAND
        return FrequencyBand.HIGH_BAND

    def dbm_power(self) -> int:
        if self.frequency_band == FrequencyBand.HIGH_BAND:
            return 1 if self.frequency < 900000000 else 0
        elif self.frequency_band == FrequencyBand.MIDDLE_BAND:
            return 2
        elif self.frequency_band == FrequencyBand.LOW_BAND:
            return 3
        elif self.frequency_band == FrequencyBand.VERY_LOW_BAND:
            return 4

    def power_factors(self) -> List[float]:
        if self.frequency_band == FrequencyBand.HIGH_BAND:
            if self.frequency < 900000000:
                return -2.04,23.45,-2.04,23.45,-1.95,27.66
            return -2.11,25.66,-2.11,25.66,-2.00,31.28
        elif self.frequency_band == FrequencyBand.MIDDLE_BAND:
            return [-3.48,38.45,-1.89,27.66,-1.92,30.23],   # 433
        elif self.frequency_band == FrequencyBand.LOW_BAND:
            return [-3.27,35.43,-1.80,26.31,-1.89,29.61],   # 315
        elif self.frequency_band == FrequencyBand.VERY_LOW_BAND:
            return [-4.18,50.66,-1.80,30.04,-1.86,32.22],   # 169

    def search_wcp(self) -> int:
        """ Returns the charge pump word for given VCO frequency. """
        vcofreq = (self.frequency / 1000000) * self.band_factor()
        vectnVCOFreq = [
            4644, 4708, 4772, 4836, 4902, 4966, 5030, 5095,
            5161, 5232, 5303, 5375, 5448, 5519, 5592, 5663
        ]
        i = 0

        if vcofreq >= vectnVCOFreq[15]:
            i = 15
        else:
            for j in range(15):
                if vcofreq < vectnVCOFreq[j]:
                    i = j
                    break

            if i != 0 and vectnVCOFreq[i] - vcofreq > vcofreq - vectnVCOFreq[i-1]:
                i -= 1
        return i % 8

    def synt_reg_values(self, digital_divider:bool, xtal:int) -> List[int]:
        div_factor = int(digital_divider) + 1
        synth_word = int(self.frequency * self.half_band_factor() * ((FBASE_DIVIDER * div_factor) / xtal))
        return [
            (self.search_wcp() << 5) + ((synth_word >> 21) & 0x1F),
            ((synth_word >> 13) & 0xFF),
            ((synth_word >> 5) & 0xFF),
            ((synth_word & 0x1F) << 3) + self.band_reg_value()
        ]

    def _frequency_band(self) -> FrequencyBand:
        if 778000000 <= self.frequency <= 957100000:
            return FrequencyBand.HIGH_BAND
        elif 386000000 <= self.frequency <= 471100000:
            return FrequencyBand.MIDDLE_BAND
        elif 299000000 <= self.frequency <= 349100000:
            return FrequencyBand.LOW_BAND
        elif 149000000 <= self.frequency <= 175100000:
            return FrequencyBand.VERY_LOW_BAND
        return FrequencyBand.HIGH_BAND

    @classmethod
    def _band_factor(cls, band:FrequencyBand) -> int:
        if band == FrequencyBand.VERY_LOW_BAND:
            return 32
        elif band == FrequencyBand.LOW_BAND:
            return 16
        elif band == FrequencyBand.MIDDLE_BAND:
            return 12
        elif band == FrequencyBand.HIGH_BAND:
            return 6
        return 6

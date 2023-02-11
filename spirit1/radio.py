import logging
import math

from typing import List

from . import Spirit1
from .constants import Spirit1Modulation
from .registers import Spirit1Registers
from .frequency import Frequency

logger = logging.getLogger(__name__)


PPM_FACTOR = 1000000  # 2e6
FBASE_DIVIDER   = 262144   # 2^18
CHSPACE_DIVIDER = 32768    # 2^15
DOUBLE_XTAL_THR = 30000000 # Threshold for double XTAL frequency


class Radio:
    DEFAULTS = {
        'base_frequency': int(868.0e6),
        'channel_space': int(20e3),
        'channel_number': 0,
        'modulation': Spirit1Modulation.GFSK_BT1,
        'datarate': 50000,
        'freq_deviation': int(20e3),
        'bandwidth': 100.5e3,
    }

    def __init__(self, spirit:Spirit1):
        self.spirit = spirit
        self.set_xtal_frequency(26e6)
        for k,v in self.DEFAULTS.items():
            setattr(self, k, v)

        self.frequency_base:Frequency = None
        self.digital_divider:bool = False
        self.reference_divider:bool = False
        self.frequency_offset:int = 0

        self.update_from_device()

    def get_settings(self) -> dict:
        rv = {}
        for k in self.DEFAULTS.keys():
            rv[k] = getattr(self, k) if hasattr(self, k) else self.DEFAULTS[k]
        return rv

    def validate(self) -> bool:
        if not 100 < self.datarate <510000:
            logger.error("Invalid datarate selected. Must be between 100 and 510000.")
            return False
        if not self.frequency_base.is_possible():
            logger.error("Invalid base frequency. Outwith permitted bands.")
            return False
        return True

    def update_from_device(self):
        """ Read various setting from the device. """
        self.get_reference_divider()
        self.get_channel_number()
        self.get_channel_space()
        self.get_frequency_base()
        self.get_frequency_offset()
        self.get_datarate()

    def init_device(self):
        # Switch off external SMPS.
        self.spirit.set_register_bit(Spirit1Registers.PM_CONFIG_2, 5, False)
        # Set the higher SEL_TSPLIT time.
        self.spirit.set_register_bit(Spirit1Registers.SYNTH_CONFIG_LO, 7, True)
        # Enable DEM 
        self.spirit.set_register_bit(Spirit1Registers.DEM_CONFIG, 1, False)

        self.write_if_offsets()
        self.write_frequency_offset()
        self.write_channel_number()
        self.write_channel_space()
        self.write_datarate_me()
        self.write_frequency_deviation_me()
        self.write_channel_bandwidth_me()
        self.write_modulation()

        self.spirit.set_register_bit(Spirit1Registers.AFC_2, 7, True)
        # Set the IQC correction optimal values
        self.spirit.write_registers(Spirit1Registers.IQC_1, 0x80, 0xE3)

        self.write_frequency_base()

    def set_xtal_frequency(self, xtal:int):
        """ Set the XTAL frequency """
        self.xtal_frequency = int(xtal)
        self.set_digital_divider(xtal > DOUBLE_XTAL_THR)
        if xtal > DOUBLE_XTAL_THR:
             xtal /= 2
        self.spirit.set_register_bit(Spirit1Registers.ANA, 6, xtal >= 25e6)

    def get_reference_divider(self):
        self.reference_divider = not self.spirit.get_register_bit(Spirit1Registers.XO_RCO_TEST, 3)

    def set_reference_divider(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.XO_RCO_TEST, 3, not onoff)

    def get_digital_divider(self):
        """ Get the current setting of the digital dividers. True = Enabled. """
        self.digital_divider = self.spirit.get_register_bit(Spirit1Registers.SYNTH_CONFIG_HI, 7)

    def set_digital_divider(self, onoff:bool):
        """ Enable/disable the digital dividers. True = Enable. """
        if not self.spirit.standby():
            logger.warning("Unable to change to standby to set the digital divider flag")
            return
        self.spirit.set_register_bit(Spirit1Registers.SYNTH_CONFIG_HI, 7, onoff)
        self.spirit.ready()
        self.digital_divider = onoff

    def get_channel_number(self):
        self.channel_number = self.spirit.read_registers(Spirit1Registers.CHANNEL_NUMBER)[0] & 0xff

    def set_channel_number(self, chan:int):
        self.channel_number = chan
        self.write_channel_number()

    def write_channel_number(self):
        self.spirit.write_registers(Spirit1Registers.CHANNEL_NUMBER, self.channel_number)

    def get_channel_space(self):
        ch_space_factor = self.spirit.read_registers(Spirit1Registers.CHANNEL_SPACE_FACTOR)[0]
        self.channel_space = int((ch_space_factor * self.xtal_frequency) / CHSPACE_DIVIDER)

    def set_channel_space(self, space:int):
        self.channel_space = space
        self.write_channel_space()

    def write_channel_space(self):
        ch_space_factor = math.floor((self.channel_space * CHSPACE_DIVIDER) / self.xtal_frequency) + 1
        self.spirit.write_registers(Spirit1Registers.CHANNEL_SPACE_FACTOR, ch_space_factor)

    def get_frequency_offset(self):
        vals = self.spirit.read_registers(Spirit1Registers.FC_OFFSET_HI, Spirit1Registers.FC_OFFSET_LO)
        self.frequency_offset = int(( (((vals[0] & 0x0F) << 8) + vals[1]) * self.xtal_frequency) / FBASE_DIVIDER)

    def set_frequency_offset(self, offset:int):
        self.frequency_offset = offset
        self.write_frequency_offset()

    def write_frequency_offset(self):
        factor = int((((self.frequency_offset * self.frequency_base.frequency) / PPM_FACTOR) * FBASE_DIVIDER) / self.xtal_frequency)
        self.spirit.update_register(Spirit1Registers.FC_OFFSET_HI, 0xF0, (factor >> 8) & 0x0F)
        self.spirit.write_registers(Spirit1Registers.FC_OFFSET_LO, factor & 0xFF)

    def get_synth_word(self) -> int:
        vals = self.spirit.read_registers(Spirit1Registers.SYNT_3, 
                                          Spirit1Registers.SYNT_2, 
                                          Spirit1Registers.SYNT_1, 
                                          Spirit1Registers.SYNT_0)
        return ((vals[0] & 0x1F) << 21) + (vals[1] << 13) + (vals[2] << 5) + ((vals[3] & 0xF8) >> 3)

    def get_frequency_base(self):
        synth_word:int = self.get_synth_word()
        band:int = self._get_band()
        self.frequency_base = Frequency.calculate(synth_word, self.xtal_frequency, self.reference_divider, band)

    def set_frequency_base(self, freq:int):
        poss = Frequency(freq)
        if not poss.is_possible():
            logger.warning("Unable to set the new base frequency to %d as it's ouwith permitted bands", freq)
            return False
        self.frequency_base = poss
        self.write_frequency_base()

    def set_modulation_scheme(self, scheme:Spirit1Modulation):
        self.modulation = scheme
        self.write_modulation()

    def write_modulation(self):
        self.spirit.update_register(Spirit1Registers.MOD0, 0x8F, self.modulation.value)

    def write_if_offsets(self):
        if_off= (3.0 * 480140) / (self.xtal_frequency >> 12) - 64
        self.spirit.write_registers(Spirit1Registers.IF_OFFSET_ANA, round(if_off))
    
        if self.xtal_frequency >= DOUBLE_XTAL_THR:
            if_off= (3.0 * 480140) / (self.xtal_frequency >> 13) - 64
        self.spirit.write_registers(Spirit1Registers.IF_OFFSET_DIG, round(if_off))

    def write_frequency_base(self, do_calibration:bool=True):
        """ Sets the synth word and the band select registers according to the
            provided base frequency.
        """
        fc = self.frequency_base.offset(self.frequency_offset + self.channel_space * self.channel_number)
        self.spirit.update_register(Spirit1Registers.SYNTH_CONFIG_HI, 0xF9, fc.vco().value)
        self.spirit.write_registers(Spirit1Registers.SYNT_3, *fc.synt_reg_values(self.reference_divider, self.xtal_frequency))
  
        if do_calibration:
            if not self.vco_calibration():
                logger.warning("Unable to calibrate the base frequency %d", fc.frequency)

    def get_datarate(self):
        factor = 5 + int(self.digital_divider)
        val = self.spirit.read_registers(Spirit1Registers.MOD1, Spirit1Registers.MOD0)
        self.datarate = ((self.xtal_frequency >> factor) * (256 + val[0])) >> (23 - (val[1] & 0x0f))

    def set_datarate(self, rate:int):
        self.datarate = rate
        self.write_datarate_me()

    def write_datarate_me(self):
        pce:int = -1
        factor:int = 20 + int(self.digital_divider)
        for i in range(15, -1, -1):
            if self.datarate >= (self.xtal_frequency >> int(factor - i)):
                pce = i
                break

        if pce == -1:
            pce = 0
        self.spirit.update_register(Spirit1Registers.MOD0, 0xF0, pce)

        pcm = -1
        factor = 5 + int(self.digital_divider)
        # Calculate the mantissa value according to the datarate formula */
        mantissa_tmp = int((self.datarate * ((1 << (23 - i)) / (self.xtal_frequency >> factor)))) - 256
        # Find the mantissa value with less approximation
        mantissa_calc:list[int] = [0, 0, 0]
        for j in range(3):
            if mantissa_tmp + j - 1:
                mantissa_calc[j] = self.datarate - (((256 + mantissa_tmp + j - 1) * (self.xtal_frequency >> factor)) >> (23 - i))
            else:
                mantissa_calc[j] = 0x7FFF

        mantissa_calc_delta = 0xFFFF
        for j in range(3):
            if abs(mantissa_calc[j]) < mantissa_calc_delta:
                mantissa_calc_delta = abs(mantissa_calc[j])
                pcm = mantissa_tmp + j - 1
        self.spirit.write_registers(Spirit1Registers.MOD1, pcm)

    def write_frequency_deviation_me(self):
        xtal_div_tmp = self.xtal_frequency / (1 << 18)

        pce:int = 0
        for i in range(10):
            a = xtal_div_tmp * (7.5 * (1 << i))
            if self.freq_deviation < a:
                pce = i
                break
        self.spirit.update_register(Spirit1Registers.FDEV0, 0x0F, (pce << 4))

        b = 0
        bp = 0
        for i in range(8):
            bp = b
            b = xtal_div_tmp * ((8 + i) / 2 * (1 << pce))
            if self.freq_deviation < b:
                pcm = i
                break
        if self.freq_deviation - bp < b - self.freq_deviation:
            pcm -= 1
        self.spirit.update_register(Spirit1Registers.FDEV0, 0xF8, (pcm & 0x07))

    def write_channel_bandwidth_me(self):
        dig_divider = 1 if self.digital_divider else 2
        chflt_factor = (self.xtal_frequency / dig_divider) / 100
        s_vectnBandwidth26M:list[int] = [
            8001, 7951, 7684, 7368, 7051, 6709, 6423, 5867, 5414,
            4509, 4259, 4032, 3808, 3621, 3417, 3254, 2945, 2703,
            2247, 2124, 2015, 1900, 1807, 1706, 1624, 1471, 1350,
            1123, 1062, 1005,  950,  903,  853,  812,  735,  675,
            561,  530,  502,  474,  451,  426,  406,  367,  337,
            280,  265,  251,  237,  226,  213,  203,  184,  169,
            140,  133,  126,  119,  113,  106,  101,   92,   84,
            70,   66,   63,   59,   56,   53,   51,   46,   42,
            35,   33,   31,   30,   28,   27,   25,   23,   21,
            18,   17,   16,   15,   14,   13,   13,   12,   11
        ]

        me = 0
        for j in range(90):
            if self.bandwidth >= (s_vectnBandwidth26M[j] * chflt_factor) / 2600:
                me = j
                break

        if me != 0:
            me_tmp = me
            chfltCalculation:list[int] = [0, 0, 0]
            for j in range(3):
                if (me_tmp + j - 1) >= 0 or (me_tmp + j - 1) <= 89:
                    chfltCalculation[j] = self.bandwidth - (s_vectnBandwidth26M[me_tmp + j -1] * chflt_factor) / 2600
                else:
                    chfltCalculation[j] = 0x7FFF

            chfltDelta = 0xFFFF
            for j in range(3):
                if abs(chfltCalculation[j]) < chfltDelta:
                    chfltDelta = abs(chfltCalculation[j])
                    me = me_tmp + j - 1
        val = ((int(me % 9) & 0x0f) << 4) + (int(me / 9) & 0x0f)
        self.spirit.write_registers(Spirit1Registers.CHFLT, val)

    # VCO
    def vco_calibration(self) -> bool:
        c_standby:bool = False
        c_restore:bool = False

        if self.xtal_frequency > DOUBLE_XTAL_THR and not self.reference_divider:
            c_restore = True
            self.set_reference_divider(True)
            self.write_frequency_base(False)

        # Increase the VCO current
        self.spirit.write_registers(Spirit1Registers.VCO_CONFIG, 0x19)
  
        self.enable_vco_calibration(True)

        self.spirit.refresh_status()
        if self.spirit.is_standby():
            c_standby = True
            if not self.spirit.ready():
                return False
        
        if not self.spirit.lock_tx():
            return False
        
        vcoTx = self.get_vco_calibration_data()

        if not self.spirit.ready():
            return False
 
        if not self.spirit.lock_rx():
            return False
        
        vcoRx = self.get_vco_calibration_data()

        if not self.spirit.ready():
            return False
  
        if c_standby:
            self.spirit.standby()
        
        self.enable_vco_calibration(False)

        # Restore the VCO current
        self.spirit.write_registers(Spirit1Registers.VCO_CONFIG, 0x11)

        if c_restore:
            self.set_reference_divider(False)
            self.write_frequency_base()

        self.set_vco_calibration_data_tx(vcoTx)
        self.set_vco_calibration_data_rx(vcoRx)
  
        return True

    def enable_vco_calibration(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_2, 1, onoff)

    def enable_rco_calibration(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_2, 2, onoff)

    def get_vco_calibration_data(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.RCO_VCO_CALIBR_OUT0)[0] & 0x7F

    def set_vco_calibration_data_tx(self, cal:int):
        self.spirit.write_registers(Spirit1Registers.RCO_VCO_CALIBR_IN1, cal)

    def set_vco_calibration_data_rx(self, cal:int):
        self.spirit.write_registers(Spirit1Registers.RCO_VCO_CALIBR_IN0, cal)

    def set_afc_freeze_on_sync(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.AFC_2, 7, onoff)

    def get_agc(self) -> bool:
        return self.spirit._get_register_bit(Spirit1Registers.AGCCTRL_0, 7)

    def set_agc(self, onoff:bool):
        self.spirit.set_register_bit(Spirit1Registers.AGCCTRL_0, 7, onoff)

    # Power management
    def set_pa_level_dbm(self, idx:int, pwr:float) -> bool:
        if not 0 <= idx <= 7:
            logger.warning("Incorrect index for Power Level. Must be between 0 and 7 not %d", idx)
            return False
        paLevelValue = self.get_dbm_2_reg(pwr)
        try:
            register = Spirit1Registers[f"PA_POWER_{7 - idx}"]
        except KeyError:
            logger.warning("Unable to find a power register for level %d", idx)
            return False
        #address = 0x10 + 7 - idx
        self.spirit.write_registers(register, paLevelValue)
        return True

    def set_pa_level_max_index(self, idx:int) -> bool:
        """ Sets a specific PA_LEVEL_MAX_INDEX. """
        if idx < 0 or idx > 7:
            logger.warning("Invalid index for max power level index. Must be between 0 and 7.")
            return False
        self.spirit.update_register(Spirit1Registers.PA_POWER_0, 0xF8, idx)
        return True

    def get_dbm_2_reg(self, pwr:float) -> int:
        """ Returns the PA register value that corresponds to the passed dBm power. """
        pwr_factors:List = self.frequency_base.power_factors()

        if pwr > 0 and (13.0 / pwr_factors[2] - pwr_factors[3] / pwr_factors[2]) < pwr:
            reg = pwr_factors[0] * pwr + pwr_factors[1]
        elif pwr <= 0 and (40.0 / pwr_factors[2] - pwr_factors[3] / pwr_factors[2]) > pwr:
            reg = pwr_factors[4] * pwr + pwr_factors[5]
        else:
            reg = pwr_factors[2] * pwr + pwr_factors[3]

        if reg < 1:
            reg = 1
        elif reg > 90:
            reg = 90
        return reg

    # Internal functions...
    def _get_band(self) -> int:
        return self.spirit.read_registers(Spirit1Registers.SYNT_0)[0] & 0x07

    def _get_synth_word(self) -> int:
        vals = self.spirit.read_registers(Spirit1Registers.SYNT_3, 
                                          Spirit1Registers.SYNT_2, 
                                          Spirit1Registers.SYNT_1, 
                                          Spirit1Registers.SYNT_0)
        return ((vals[0] & 0x1F) << 21) + (vals[1] << 13) + (vals[2] << 5) + ((vals[3] & 0xF8) >> 3)

import unittest

from spirit1.csma import CSMA, CCALength, CCAPeriod, CSMAConfig
from spirit1.irq import IRQ, IRQConfig, SpiritIrq
from spirit1.qi import QI, QIConfig
from spirit1.timer import Timer, TimerConfig


class RecordingDevice:
    def __init__(self):
        self.calls = []

    def write_registers(self, register, *values):
        self.calls.append(("write", register, values))

    def update_register(self, register, mask, value):
        self.calls.append(("update", register, mask, value))

    def set_register_bit(self, register, bit, value):
        self.calls.append(("bit", register, bit, value))


class PeripheralConfigTests(unittest.TestCase):
    def test_qi_apply_writes_one_complete_configuration_value(self):
        device = RecordingDevice()

        self.assertTrue(QI(device, QIConfig(3, True, 10, True)).apply())

        self.assertEqual(device.calls[0][2], (0xEB,))

    def test_timer_apply_writes_all_timeout_settings(self):
        device = RecordingDevice()
        config = TimerConfig(26_000_000, 7, 8, True, True, False, True)

        self.assertTrue(Timer(device, config).apply())

        self.assertEqual(device.calls[0][0], "update")
        self.assertEqual(device.calls[-1][2], (8, 7))

    def test_csma_apply_encodes_seed_and_prescaler_as_bytes(self):
        device = RecordingDevice()
        config = CSMAConfig(
            enabled=True,
            cca_period=CCAPeriod.TBitTime_256,
            cca_length=CCALength.CcaTime_3,
            max_backoffs=4,
            backoff_counter_seed=0xABCD,
            backoff_prescaler=5,
        )

        self.assertTrue(CSMA(device, config).apply())

        self.assertEqual(device.calls[0][2], (0xAB, 0xCD, 0x16, 0x34))

    def test_irq_apply_encodes_enabled_flags_as_a_32_bit_mask(self):
        device = RecordingDevice()
        config = IRQConfig({SpiritIrq.RX_DATA_READY, SpiritIrq.RX_TIMEOUT})

        IRQ(device, config).apply()

        self.assertEqual(device.calls[0][2], (0x20, 0x00, 0x00, 0x01))

import unittest

import spirit1


class PackageMetadataTests(unittest.TestCase):
    def test_public_version(self):
        self.assertEqual(spirit1.__version__, "0.1.1")

    def test_public_driver_export(self):
        self.assertIn("Spirit1Device", spirit1.__all__)

    def test_public_received_message_export(self):
        self.assertIn("ReceivedMessage", spirit1.__all__)

    def test_public_basic_packet_exports(self):
        self.assertIn("BasicPacket", spirit1.__all__)
        self.assertIn("BasicPacketConfig", spirit1.__all__)

    def test_public_radio_and_receiver_exports(self):
        self.assertIn("Radio", spirit1.__all__)
        self.assertIn("Receiver", spirit1.__all__)

    def test_public_gpio_exports(self):
        self.assertIn("ShutdownPin", spirit1.__all__)
        self.assertIn("open_gpiozero_sdn", spirit1.__all__)

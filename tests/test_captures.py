"""Regression tests using messages captured from a real SPIRIT1 receiver."""

import json
import unittest
from pathlib import Path

from spirit1.basic_packet import BasicPacket, BasicPacketConfig
from spirit1.enums import CrcMode
from spirit1.receiver import ReceivedMessage

CAPTURES = Path(__file__).parent / "fixtures" / "captures.jsonl"


def received_message(record: dict) -> ReceivedMessage:
    """Recreate the receiver snapshot stored by ``capture_messages.py``."""
    return ReceivedMessage(
        payload=bytearray.fromhex(record["payload"]),
        crc_valid=record["crc_valid"],
        rssi=record["rssi"],
        sqi=record["sqi"],
        pqi=record["pqi"],
        agc_word=record["agc_word"],
        source_address=record["source_address"],
        destination_address=record["destination_address"],
        control_data=bytes.fromhex(record["control_data"]),
        crc=bytes.fromhex(record["crc"]),
    )


class CapturedPacketTests(unittest.TestCase):
    def test_captured_messages_decode_to_the_recorded_fields(self):
        records = [json.loads(line) for line in CAPTURES.read_text().splitlines() if line]
        packet = BasicPacket(None, BasicPacketConfig(
            control_length=4,
            address_field=True,
            crc_mode=CrcMode.CRC_MODE_864CBF,
        ))

        self.assertEqual(len(records), 10)
        for record in records:
            with self.subTest(payload=record["payload"]):
                message = packet.decode(received_message(record))

                self.assertEqual(message.payload, bytes.fromhex(record["payload"]))
                self.assertEqual(message.source_address, record["source_address"])
                self.assertEqual(message.destination_address, record["destination_address"])
                self.assertEqual(message.control_data, bytes.fromhex(record["control_data"]))
                self.assertEqual(message.crc, bytes.fromhex(record["crc"]))
                self.assertEqual(message.crc_valid, record["crc_valid"])
                self.assertEqual(message.rssi, record["rssi"])
                self.assertEqual(message.sqi, record["sqi"])
                self.assertEqual(message.pqi, record["pqi"])
                self.assertEqual(message.agc_word, record["agc_word"])

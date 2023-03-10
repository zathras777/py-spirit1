import logging

from typing import List

from . import Spirit1
from .constants import CrcMode
from .registers import Spirit1Registers

logger = logging.getLogger(__name__)


class BasicPacketAddress:
    def __init__(self):
        self.filter_on_my_address:bool = False
        self.my_address:int = 0x01
        self.filter_on_multicast_address:bool = False
        self.multicast_address:int = 0x01
        self.filter_on_broadcast_address:bool = False
        self.broadcast_address:int = 0x01


class BasicPacket:
    def __init__(self, spirit:Spirit1):
        self.spirit = spirit
        self.preamble_length:int = 1
        self.sync_length:int = 1
        self.sync_words:List[int] = [0x01]
        self.fixed_length:bool = False
        self.fixed_packet_length:int = 0
        self.crc_mode:CrcMode = CrcMode.CRC_MODE_OFF
        self.control_length:int = 0
        self.address_field:bool = False
        self.fec:bool = False
        self.data_whitening:bool = False

    def validate(self) -> bool:
        if not 1 <= self.preamble_length <= 32:
            logger.warning("Preamble length must be between 1 and 32 bytes, not %d", self.preamble_length)
            return False
        if not 1 <= self.sync_length <= 4:
            logger.warning("Sync Length of packet must be between 1 and 4, not %d", self.sync_length)
            return False
        if not self.crc_mode in CrcMode:
            logger.warning("Unknown CRC Mode")
            return False
        return True

    def init(self) -> bool:
        if not self.validate():
            logger.warning("Basic Packet Configuration failed validation.")
            return False

        # Enable auto packet filtering
        self.spirit.set_register_bit(Spirit1Registers.PROTOCOL_1, 0, True)

        # Disable Source and Control filtering. Enable CRC checks if required.
        fltopts = self.spirit.read_registers(Spirit1Registers.PKTFLT_OPTS)[0]
        fltopts &= 0xCE
        if self.crc_mode != CrcMode.CRC_MODE_OFF:
            fltopts = fltopts | 0x01
        self.spirit.write_registers(Spirit1Registers.PKTFLT_OPTS, fltopts)

        pktctrl:List[int] = [0, 0, 0, 0]
        pktctrl[0] = (int(self.address_field) << 3) | self.control_length
        pktctrl[1] = (self.fixed_packet_length.bit_length() - 1) & 0x0F
        pktctrl[2] = (self.preamble_length << 3) + ((self.sync_length - 1) << 1) + (0 if self.fixed_length else 1)
        pktctrl[3] = (int(self.crc_mode) << 5) + (int(self.data_whitening) << 4) + int(self.fec)
        self.spirit.write_registers(Spirit1Registers.PKTCTRL_4, *pktctrl)
        # Write the sync words
        self.spirit.write_registers(Spirit1Registers.SYNC_4, *(reversed(self.sync_words[:4])))

        return True

    def set_packet_length(self, sz:int):
        wid = (sz.bit_length() - 1) & 0x0F
        self.spirit.update_register(Spirit1Registers.PKTCTRL_3, 0xF0, wid)
#        tmp = self.spirit.read_registers(Spirit1Registers.PKTCTRL_3)[0]
#        tmp = (tmp & 0xF0) + wid
#        self.spirit.write_registers(0x31, tmp)



    def settings(self):
        pktctrl = self.spirit.read_registers(Spirit1Registers.PKTCTRL_4, 
                                             Spirit1Registers.PKTCTRL_3, 
                                             Spirit1Registers.PKTCTRL_2, 
                                             Spirit1Registers.PKTCTRL_1)
        rv = "Basic Packet Settings:\n"
        rv += f"  Registers: 0x30 {pktctrl[0]:02x} {pktctrl[0]:08b}\n"
        rv += f"             0x31 {pktctrl[1]:02x} {pktctrl[1]:08b}\n"
        rv += f"             0x32 {pktctrl[2]:02x} {pktctrl[2]:08b}\n"
        rv += f"             0x33 {pktctrl[3]:02x} {pktctrl[3]:08b}\n"
        rv += f"  address field:   0x{(pktctrl[0] >> 3):02x}\n"
        rv += f"  control length:  {(pktctrl[0] & 0x07)} bytes\n"
        rv += f"  packet format:   {(pktctrl[1] >> 6)}\n"
        rv += f"  rx mode:         {(pktctrl[1] >> 4) & 0x03}\n"
        rv += f"  packet length:   {(pktctrl[1] & 0x0f) + 1} bits (max {1 << ((pktctrl[1] & 0x0f) + 1)} bytes)\n"
        rv += f"  preamble length: {(pktctrl[2] >> 3)} bytes\n"
        rv += f"  # of sync words: {((pktctrl[2] >> 1) & 0x03) + 1}\n"
        crc:CrcMode = CrcMode(pktctrl[3] >> 5)
        rv += f"  CRC Mode:        {crc.name}\n"
        rv += f"  tx mode:         {(pktctrl[3] >> 2) & 0x03}\n"
        rv += "  Packets are of a fixed length\n" if (pktctrl[2] & 0x01) == 0x0 else "  Variable length packets\n"
        rv += "  Data is being whitened\n" if (pktctrl[3] & 0x10) == 0x10 else ""
        rv += "  FEC enabled\n" if (pktctrl[3] & 0x01) == 0x01 else ""
        syncw = self.spirit.read_registers(Spirit1Registers.SYNC_4, 
                                           Spirit1Registers.SYNC_3, 
                                           Spirit1Registers.SYNC_2, 
                                           Spirit1Registers.SYNC_1)
        rv += f"  SYNC Words: 0x{syncw[3]:02x} 0x{syncw[2]:02x} 0x{syncw[1]:02x} 0x{syncw[0]:02x}\n"
        rv += "Packet Filtering Options:\n"
        pktflt = self.spirit.read_registers(Spirit1Registers.PKTFLT_OPTS)[0]
        rv += f"  RX Timeout AND/OR selection:  {(pktflt & (1 << 6)) == (1<<6)}\n"
        rv += f"  Control Filtering:            {(pktflt & (1 << 5)) == (1<<5)}\n"
        rv += f"  Source Filtering:             {(pktflt & (1 << 4)) == (1<<4)}\n"
        rv += f"  Destination vs Source:        {(pktflt & (1 << 3)) == (1<<3)}\n"
        rv += f"  Destination vs Multicast:     {(pktflt & (1 << 2)) == (1<<2)}\n"
        rv += f"  Destination vs Broadcast:     {(pktflt & (1 << 1)) == (1<<1)}\n"
        rv += f"  CRC Validation:               {(pktflt & (1 << 0)) == (1<<0)}\n"

        return rv
    


    def get_received_packet_length(self) -> int:
        oversize = 1 if self.address_field else 0
        # add control length to oversize...

        vals = self.spirit.read_registers(Spirit1Registers.RX_PKT_LEN_HI, Spirit1Registers.RX_PKT_LEN_LO)
        return ((vals[0] << 8) + vals[1]) - oversize


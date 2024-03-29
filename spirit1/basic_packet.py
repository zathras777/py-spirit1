import logging
import time

from typing import List, Optional

from . import Spirit1
from .constants import CrcMode
from .registers import Spirit1Registers
from .receiver import ReceivedMessage

logger = logging.getLogger(__name__)


class BasicPacketMessage:
    def __init__(self):
        self.address:Optional(int) = None
        self.ctrl_data:Optional(List[int]) = None
        self.payload:Optional(bytes) = None
        self.encoded:Optional(bytes) = None
        self.rssi:Optional(int) = None
        self.sqi:Optional(int) = None
        self.pqi:Optional(int) = None
        self.agc_word:Optional(int) = None
        self.crc_fields:Optional(List[int]) = None

    @classmethod
    def from_received_message(cls, base:ReceivedMessage, addr:Optional[int], ctrl_data:Optional[list[int]], crc:Optional[list[int]]):
        obj = cls()
        obj.address = addr
        obj.ctrl_data = ctrl_data
        obj.payload = base.payload
        obj.rssi = base.rssi
        obj.sqi = base.sqi
        obj.pqi = base.pqi
        obj.agc_word = base.agc_word
        obj.crc_fields = crc
        return obj

    def __repr__(self) -> str:
        return f"Basic Packet Message: {len(self.payload)} bytes"

    def info(self, inc_quality:bool=True) -> str:
        info_str = "Message: \n"
        if self.address is not None:
            info_str += f"  From Address: 0x{self.address:02x}\n"
        if self.ctrl_data is not None and len(self.ctrl_data) > 0:
            ctrl = " ".join(f"{x:02x}" for x in self.ctrl_data)
            info_str += f"  Control Data: {ctrl}\n"
        if self.crc_fields is not None and len(self.crc_fields) > 0:
            crc = " ".join(f"{x:02x}" for x in self.crc_fields)
            info_str += f"  CRC Data:     {crc}\n"
        if inc_quality:
            info_str += f"  RSSI: {self.rssi}  SQI: {self.sqi}  PQI: {self.pqi}  AGC_WORD: {self.agc_word}\n"
        pl = " ".join([f"{x:02x}" for x in self.payload])
        info_str += f"  Payload: {pl}\n"
        return info_str

    def one_line(self) -> str:
        one_line = ""
        if self.address is not None:
            one_line += f"{self.address:02x} "
        if self.ctrl_data is not None and len(self.ctrl_data) > 0:
            ctrl = " ".join(f"{x:02x}" for x in self.ctrl_data)
            one_line += f"{ctrl} "
        pl = " ".join([f"{x:02x}" for x in self.payload])
        return one_line + pl


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

    def get_crc(self):
        if self.crc_mode == CrcMode.CRC_MODE_OFF:
            return None
        reg = Spirit1Registers.CRC_FIELD_2
        len = 3
        if self.crc_mode in [CrcMode.CRC_MODE_7]:
            reg = Spirit1Registers.CRC_FIELD_0
            len = 1
        elif self.crc_mode in [CrcMode.CRC_MODE_1021, CrcMode.CRC_MODE_8005]:
            reg = Spirit1Registers.CRC_FIELD_1
            len = 2
        crc = list(self.spirit.read_n_registers(reg, len))
        crc.reverse()
        return crc

    def get_ctrl_data(self):
        if self.control_length == 0:
            return None
        reg = Spirit1Registers.RX_CTRL_FIELD_3
        len = 4
        if self.control_length == 3:
            reg = Spirit1Registers.RX_CTRL_FIELD_2
            len = 3
        elif self.control_length == 2:
            reg = Spirit1Registers.RX_CTRL_FIELD_1
            len = 2
        elif self.control_length == 1:
            reg = Spirit1Registers.RX_CTRL_FIELD_0
            len = 1
        
        ctrl_data = list(self.spirit.read_n_registers(reg, len))
        #ctrl_data.reverse()
        return ctrl_data

    def set_tx_ctrl_data(self, data:list):
        if self.control_length > 0:
            if len(data) < self.control_length:
                raise ValueError(f"Basic Packet configured for {self.control_length} control fields, only {len(msg.ctrl_data)} supplied")
        reg:Spirit1Registers = Spirit1Registers.TX_CTRL_3
        if self.control_length == 3:
            reg = Spirit1Registers.TX_CTRL_2
        elif self.control_length == 2:
            reg = Spirit1Registers.TX_CTRL_1
        elif self.control_length == 1:
            reg = Spirit1Registers.TX_CTRL_0
        rev_list = data[:self.control_length]
        #rev_list.reverse()
        self.spirit.write_registers(reg, *rev_list)

    def set_payload_length(self, p_len:int):
        total_len = p_len + self.control_length
        if self.address_field:
            total_len += 1
        data = [(total_len >> 8) & 0xff, total_len & 0xff]
        self.spirit.write_registers(Spirit1Registers.PKTLEN_1, *data)
 
    def set_packet_length(self, sz:int):
        wid = (sz.bit_length() - 1) & 0x0F
        self.spirit.update_register(Spirit1Registers.PKTCTRL_3, 0xF0, wid)

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

        vals = self.spirit.read_n_registers(Spirit1Registers.RX_PKT_LEN_HI, 2)
        return ((vals[0] << 8) + vals[1]) - oversize

    def get_message(self, base:ReceivedMessage) -> BasicPacketMessage:
        addr:Optional[int] = None

        if self.address_field:
            addr = self.spirit.read_registers(Spirit1Registers.RX_ADDRESS_0)[0]
        ctrl_data = self.get_ctrl_data()
        crc = self.get_crc()
        return BasicPacketMessage.from_received_message(base, addr, ctrl_data, crc)

    def send_message(self, msg:BasicPacketMessage) -> bool:
        if self.address_field:
            if msg.address is None:
                raise ValueError("Basic Packet configured for address, but none supplied")
            self.spirit.write_registers(Spirit1Registers.RX_SOURCE_ADDR, msg.address)
        self.set_tx_ctrl_data(msg.ctrl_data)

        if self.fixed_length:
            self.set_payload_length(len(msg.payload))

        self.spirit.flush_tx_fifo()
        self.spirit.write_linear_fifo(list(msg.payload))

        if not self.spirit.start_tx():
            return False
        
        while self.spirit.linear_fifo_tx_size() != 0:
            time.sleep(1)

        return True
    
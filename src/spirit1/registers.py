from enum import IntEnum


class Spirit1Registers(IntEnum):
    ANA = 0x01
    IF_OFFSET_ANA = 0x07          # Analog intermediate offset
    SYNT_3 = 0x08                 # PLL Programmable Divider
    SYNT_2 = 0x09                 # PLL Programmable Divider
    SYNT_1 = 0x0A                 # PLL Programmable Divider
    SYNT_0 = 0x0B                 # PLL Programmable Divider
    CHANNEL_SPACE_FACTOR = 0x0C   # Factored channel space
    IF_OFFSET_DIG = 0x0D          # Digital intermediate offset

    FC_OFFSET_HI = 0x0E
    FC_OFFSET_LO = 0x0F
    
    PA_POWER_8 = 0x10
    PA_POWER_7 = 0x11
    PA_POWER_6 = 0x12
    PA_POWER_5 = 0x13
    PA_POWER_4 = 0x14
    PA_POWER_3 = 0x15
    PA_POWER_2 = 0x16
    PA_POWER_1 = 0x17
    PA_POWER_0 = 0x18

    MOD1 = 0x1A
    MOD0 = 0x1B
    FDEV0 = 0x1C
    CHFLT = 0x1D                  # Channel Filter
    AFC_2 = 0x1E
    AFC_1 = 0x1F
    AFC_0 = 0x20
    AGCCTRL_2 = 0x24
    AGCCTRL_1 = 0x25
    AGCCTRL_0 = 0x26

    PKTCTRL_4 = 0x30
    PKTCTRL_3 = 0x31
    PKTCTRL_2 = 0x32
    PKTCTRL_1 = 0x33
    PKTLEN_1 = 0x34
    PKTLEN_0 = 0x35
    SYNC_4 = 0x36
    SYNC_3 = 0x37
    SYNC_2 = 0x38
    SYNC_1 = 0x39
    QI = 0x3A                     # SQI & PQI

    RX_SOURCE_ADDR = 0x4B
    TX_SOURCE_ADDR = 0x4E

    PKTFLT_OPTS = 0x4F
    PROTOCOL_2 = 0x50
    PROTOCOL_1 = 0x51
    PROTOCOL_0 = 0x52
    TIMERS_5 = 0x53
    TIMERS_4 = 0x54
    TIMERS_3 = 0x55
    TIMERS_2 = 0x56
    TIMERS_1 = 0x57
    TIMERS_0 = 0x58

    CSMA_CONFIG_3 = 0x64
    CSMA_CONFIG_2 = 0x65
    CSMA_CONFIG_1 = 0x66
    CSMA_CONFIG_0 = 0x67

    TX_CTRL_3 = 0x68
    TX_CTRL_2 = 0x69
    TX_CTRL_1 = 0x6A
    TX_CTRL_0 = 0x6B

    CHANNEL_NUMBER = 0x6C         # Channel number
    RCO_VCO_CALIBR_IN1 = 0x6E     # VCO Tx calibration input
    RCO_VCO_CALIBR_IN0 = 0x6F     # VCO Rx calibration input

    IRQ_MASK_3 = 0x90
    IRQ_MASK_2 = 0x91
    IRQ_MASK_1 = 0x92
    IRQ_MASK_0 = 0x93
    IQC_1 = 0x99                  # Undocumented
    IQC_0 = 0x9A                  # Undocumented
    SYNTH_CONFIG_HI = 0x9E
    SYNTH_CONFIG_LO = 0x9F

    VCO_CONFIG = 0xA1             # VCO Configuration
    DEM_CONFIG = 0xA3
    PM_CONFIG_2 = 0xA4
    PM_CONFIG_1 = 0xA5
    PM_CONFIG_0 = 0xA6

    XO_RCO_TEST = 0xB4

    LINK_QUALIF_2 = 0xC5
    LINK_QUALIF_1 = 0xC6
    LINK_QUALIF_0 = 0xC7
    RSSI_LEVEL = 0xC8             # RSSI of received packet

    RX_PKT_LEN_HI = 0xC9
    RX_PKT_LEN_LO = 0xCA

    CRC_FIELD_2 = 0xCB            # CRC Field of received packet, byte 2
    CRC_FIELD_1 = 0xCC            # CRC Field of received packet, byte 1
    CRC_FIELD_0 = 0xCD            # CRC Field of received packet, byte 0

    RX_CTRL_FIELD_3 = 0xCE        # RX Control Data Byte 0
    RX_CTRL_FIELD_2 = 0xCF        # RX Control Data Byte 1
    RX_CTRL_FIELD_1 = 0xD0        # RX Control Data Byte 2
    RX_CTRL_FIELD_0 = 0xD1        # RX Control Data Byte 3

    RX_ADDRESS_1 = 0xD2           # RX Source Address
    RX_ADDRESS_0 = 0xD3           # RX Destination Address

    RCO_VCO_CALIBR_OUT0 = 0xE5    # RCO/VCO Calibration output
    LINEAR_FIFO_STATUS_1 = 0xE6
    LINEAR_FIFO_STATUS_0 = 0xE7

    IRQ_STATUS_3 = 0xFA
    IRQ_STATUS_2 = 0xFB
    IRQ_STATUS_1 = 0xFC
    IRQ_STATUS_0 = 0xFD

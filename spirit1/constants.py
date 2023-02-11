from enum import IntEnum

class Spirit1Commands(IntEnum):
    TX                 = 0x60 # Start to transmit; valid only from READY */
    RX                 = 0x61 # Start to receive; valid only from READY */
    READY              = 0x62 # Go to READY; valid only from STANDBY or SLEEP or LOCK */
    STANDBY            = 0x63 # Go to STANDBY; valid only from READY */
    SLEEP              = 0x64 # Go to SLEEP; valid only from READY */
    LOCKRX             = 0x65 # Go to LOCK state by using the RX configuration of the synth; valid only from READY */
    LOCKTX             = 0x66 # Go to LOCK state by using the TX configuration of the synth; valid only from READY */
    SABORT             = 0x67 # Force exit form TX or RX states and go to READY state; valid only from TX or RX */
    LDC_RELOAD         = 0x68 # LDC Mode: Reload the LDC timer with the value stored in the  LDC_PRESCALER / COUNTER registers
    SEQUENCE_UPDATE    = 0x69 # Autoretransmission: Reload the Packet sequence counter with the value stored in the PROTOCOL[2] register
    AES_ENC            = 0x6A # AES: Start the encryption routine; valid from all states; valid from all states */
    AES_KEY            = 0x6B # AES: Start the procedure to compute the key for the decryption; valid from all states */
    AES_DEC            = 0x6C # AES: Start the decryption routine using the current key; valid from all states */
    AES_KEY_DEC        = 0x6D # AES: Compute the key and start the decryption; valid from all states */
    SRES	           = 0x70 # Reset of all digital part, except SPI registers */
    FLUSHRXFIFO        = 0x71 # Clean the RX FIFO; valid from all states */
    FLUSHTXFIFO        = 0x72 # Clean the TX FIFO; valid from all states */


class Spirit1State(IntEnum):
    READY   = 0x03
    LOCK    = 0x0F
    LOCKWON = 0x13
    RX      = 0x33
    SLEEP   = 0x36
    STANDBY = 0x40
    TX      = 0x5F


class Spirit1Modulation(IntEnum):
    FSK         = 0x00  # 2-FSK modulation selected
    GFSK_BT1    = 0x10  # GFSK modulation selected with BT=1
    GFSK_BT05   = 0x50  # GFSK modulation selected with BT=0.5
    ASK_OOK     = 0x20  # ASK or OOK modulation selected. ASK will use power ramping
    MSK         = 0x30  # MSK modulation selected


class CrcMode(IntEnum):
    CRC_MODE_OFF    = 0
    CRC_MODE_7      = 1
    CRC_MODE_8005   = 2
    CRC_MODE_1021   = 3
    CRC_MODE_864CBF = 4

# py-spirit1
Python library to support using the SPIRIT1 RF chip
https://www.st.com/resource/en/datasheet/spirit1.pdf

## Install

Install from a checkout:

```shell
python -m pip install .
```

On a Raspberry Pi, install both the optional SPI and GPIO dependencies:

```shell
python -m pip install '.[raspberry-pi]'
```

## Usage

```python
from spirit1 import Radio, RadioConfig, open_gpiozero_sdn, open_spidev

sdn = open_gpiozero_sdn(4)  # BCM GPIO4, physical header pin 7
spirit = open_spidev(bus=0, device=0, speed_hz=250_000, sdn=sdn)
try:
    if spirit.is_shutdown() and not spirit.wake():
        raise RuntimeError("SPIRIT1 did not respond after waking")
    if not spirit.check_communication():
        raise RuntimeError("SPIRIT1 is not responding")

    config = RadioConfig(base_frequency=868_200_000, datarate=50_000)
    radio = Radio(spirit, config)
    radio.init_device()

    # Configure and use the radio as required.
finally:
    spirit.close()
    sdn.close()

```

There is a small script that can dump the device configuration via the various SPI registers.

```shell
$ PYTHONPATH=src python examples/dump_config.py --bus 0 --device 0

SPIRIT1 configuration:
  0x01 ANA                      0xC0
  0x07 IF_OFFSET_ANA            0x36
  0x08 SYNT_3                   0x2D
  0x09 SYNT_2                   0x05
  0x0A SYNT_1                   0xE3
  0x0B SYNT_0                   0x51
  0x0C CHANNEL_SPACE_FACTOR     0x84
  0x0D IF_OFFSET_DIG            0xAC
  0x0E FC_OFFSET_HI             0x00
  0x0F FC_OFFSET_LO             0x00
  0x10 PA_POWER_8               0x03
  0x11 PA_POWER_7               0x01
  0x12 PA_POWER_6               0x1A
  0x13 PA_POWER_5               0x25
  0x14 PA_POWER_4               0x35
  0x15 PA_POWER_3               0x40
  0x16 PA_POWER_2               0x4E
  0x17 PA_POWER_1               0x00
  0x18 PA_POWER_0               0x00
  0x1A MOD1                     0x06
  0x1B MOD0                     0x5B
  0x1C FDEV0                    0x45
  ...
```

To simply view messages via the device, the example script does that using a radio configuration that works for me. It may not find any messages for you and may well need adjusting.

```shell
$ PYTHONPATH=src python examples/example.py 10
01:59:01 DEBUG selector_events - __init__: Using selector: EpollSelector
Trying to receive 10 messages.
Message: 
  From Address: 0xff
  Control Data: c6 00 07 06
  CRC Data:     d6 8e c1
  RSSI: 97  SQI: 32  PQI: 12  AGC_WORD: 8
  Payload: 05 ff 00 5c 03 e1 40 85 82 6b 80 3e fd 9b 6f 52 7d 28 38
...
```

## Background

While trying to figure out the RF communication protocol for a small remote I discovered that it used the Spirit1 RF chip. To delve further into the protocol and to simplify collection while also permitting me to have transmit ability to replace the remote entirely, I got a Nucleo IDS01A5 development board.

- https://www.st.com/en/ecosystems/x-nucleo-ids01a5.html

After attaching this to a RaspberryPi, I was able to control the chip and retrieve messages using this library.

## Inspecting Configuration

To print the device's stable configuration registers without changing its state, run:

```shell
$ PYTHONPATH=src python examples/dump_config.py --bus 0 --device 0
```

## Limitations
Presently only a fraction of the full functionality is implemented.

- Basic-packet receive and transmit support is implemented.
- STack packet configuration and decoding are experimental; automatic ACK/retry and sequence-number behavior need hardware validation.
- Wireless M-Bus packets are not implemented.
- GPIO interrupt support is not implemented.

## Status
The library has been rewritten to be more robust and provide a simpler interface.

Improvements are welcome!

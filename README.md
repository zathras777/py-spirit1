# py-spirit1
Python library to support using the SPIRIT1 RF chip

## Usage
```python
import spidev

from spirit1 import Spirit1
from spirit1.radio import Radio

# Open the SPI device
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 250000
spi.mode = 0b00

# Create the Spirit1 object using the SPI device
spirit = Spirit1(spi)
radio = Radio(spirit)
# Configure the radio as required.
radio.init_device()

...

```

```shell
$ python ./example.py 10
01:59:01 DEBUG selector_events - __init__: Using selector: EpollSelector
Trying to receive 10 messages.
Message: 
  From Address: 0xff
  Control Data: c6 00 07 06
  CRC Data:     d6 8e c1
  RSSI: 97  SQI: 32  PQI: 12  AGC_WORD: 8
  Payload: 05 ff 00 5c 03 e1 40 85 82 6b 80 3e fd 9b 6f 52 7d 28 38
```

```shell
$ python ./example.py 
16:02:46 DEBUG selector_events - __init__: Using selector: EpollSelector
Trying to receive 30 messages.
ff 53 00 39 06 05 ff 00 b4 30 06 92 44 5a 31 7b 8c 1b 70 7c e6 71 5c 8d => 19 6d 9b 66 15 ae a1 8f 6e f0 23 cc 96 d0 4c 1c
ff fc 00 32 06 05 ff 00 2e 3e c8 ce 95 da 00 ff e5 a2 86 db 1f ea b6 e8 => 02 01 0a 6c 72 38 00 00 00 00 24 01 40 d0 15 66
...
```

## Background
This project has been written to allow me to use the chip in order to control some heaters remotely. The RF controllers for these heaters use the SPIRIT1 internally, so using the same chip allows me to investigate the protocol and then hopefully emulate it.

The chip was accessed via a Nucleo IDS01A5 development board using a RaspberryPi for SPI.
- https://www.st.com/en/ecosystems/x-nucleo-ids01a5.html
- https://blog.david-reid.com/rf-controller-part-6/

Much of the structure and details of this library are from the available development library that STMicroelectronics makes available via their website. I did experiment with using their IDE but it wasn't a simple exercise and never led to any working code.

Presently the receiver is very basic and doesn't use the available physical GPIO connections. This is mainly due to not having connected them yet as I wanted to make sure that this could be made to work reliably first.

The example.py file works and captures packets between the RF controllers and the heaters. It accepts a single argument that determines how many packets the receiver will capture before exiting.

## Example Script
The example.py script has additions beyond simply accessing and controlling the SPIRIT1 chipset while I continue to investigate the controller that led to this module. These will be removed soon :-)

## Limitations
Presently only a fraction of the full functionality is implemented. To date I have focussed on what I needed, but the basics are there and adding additional fucntionality isn't difficult.
- only basic packet types are included as that's what I have been interested in
- no transmission code is yet included
- no GPIO support yet as I haven't needed it

## Next Steps
Now that this library is able to receive packets the next step is to decode the protocol. I have looked at sending data via the chip and that works as expected, though it is not yet included in the library.
The receiver is far from ideal and so moving to using a physical GPIO and possibly async code is on any future roadmap.

As always, there will be numerous bugs and much of the code can be improved, so pull requests are welcome.
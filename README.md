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

## Background
This project has been written to allow me to use the chip in order to control some heaters remotely. The RF controllers for these heaters use the SPIRIT1 internally, so using the same chip allows me to investigate the protocol and then hopefully emulate it.

The chip was accessed via a Nucleo IDS01A5 development board using a RaspberryPi for SPI.
- https://www.st.com/en/ecosystems/x-nucleo-ids01a5.html
- https://blog.david-reid.com/rf-controller-part-6/

Much of the structure and details of this library are from the available development library that STMicroelectronics makes available via their website. I did experiment with using their IDE but it wasn't a simple exercise and never led to any working code.

Presently the receiver is very basic and doesn't use the available physical GPIO connections. This is mainly due to not having connected them yet as I wanted to make sure that this could be made to work reliably first.

The example.py file works and captures packets between the RF controllers and the heaters. It accepts a single argument that determines how many packets the receiver will capture before exiting.

## Limitations
Presently only a fraction of the full functionality is implemented. To date I have focussed on what I needed, but the basics are there and adding additional fucntionality isn't difficult.
- only basic packet types are included as that's what I have been interested in
- no transmission code is yet included
- no GPIO support yet as I haven't needed it

## Next Steps
Now that this library is able to receive packets the next step is to decode the protocol. I have looked at sending data via the chip and that works as expected, though it is not yet included in the library.
The receiver is far from ideal and so moving to using a physical GPIO and possibly async code is on any future roadmap.

As always, there will be numerous bugs and much of the code can be improved, so pull requests are welcome.
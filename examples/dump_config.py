"""Print SPIRIT1 configuration registers without changing the radio state."""

import argparse

from spirit1 import Spirit1Device
from spirit1.diagnostics import dump_configuration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus", type=int, default=0, help="SPI bus number (default: 0)")
    parser.add_argument("--device", type=int, default=0, help="SPI device number (default: 0)")
    parser.add_argument("--speed", type=int, default=250_000, help="SPI speed in Hz")
    args = parser.parse_args()

    try:
        import spidev
    except ImportError as error:
        raise SystemExit("This utility requires the optional 'spidev' dependency") from error

    spi = spidev.SpiDev()
    spi.open(args.bus, args.device)
    spi.max_speed_hz = args.speed
    spi.mode = 0b00
    try:
        print(dump_configuration(Spirit1Device(spi)))
    finally:
        spi.close()


if __name__ == "__main__":
    main()

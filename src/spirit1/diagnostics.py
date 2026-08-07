"""Read-only diagnostics for inspecting a configured SPIRIT1 device."""

from .device import Spirit1Device
from .registers import Spirit1Registers


def dump_configuration(device: Spirit1Device) -> str:
    """Return the stable configuration-register values without reading RX status."""
    lines = ["SPIRIT1 configuration:"]
    registers = sorted(
        (register for register in Spirit1Registers if register.value < 0xC0),
        key=lambda register: register.value,
    )
    for register in registers:
        value = device.read_register(register)
        lines.append(f"  0x{register.value:02X} {register.name:<24} 0x{value:02X}")
    return "\n".join(lines)

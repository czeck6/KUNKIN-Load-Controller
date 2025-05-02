# KUNKIN-Load-Controller
Python tools to control a KUNKIN KP184 DC Load

# Kunkin KP184 Load Controller

A Python interface and interactive CLI for controlling the **Kunkin KP184** programmable DC electronic load over RS-232 using `pyserial`.

This was built to replace tedious manual input and allow scripting, live monitoring, and quick emergency shutdown via the keyboard.

## Features

- Control the KP184 using RS-232 (via USB-serial adapter)
- Set mode (CV, CC, CR, CW)
- Set voltage, current, resistance, and power
- Turn the load on/off
- Live polling display with power calculation
- Emergency kill (`q` key) at any time

> ⚠️ **Note:** The KP182 does **not** support serial communication. This script is only compatible with the **KP184** or equivalent models.

## Requirements

- Python 3.7+
- `pyserial`

Install via pip:

```bash
pip install pyserial
```

## Usage

Clone the repo and run the CLI:

```bash
python cli_control.py
```

You’ll be prompted to enter the serial port (`COM5`, `/dev/ttyUSB0`, etc). After that, use the number menu to interact with the load.

## Wiring Note

Most USB-RS232 adapters (like DTECH PL2303) are **DTE** devices. The KP184 is also a **DTE** device. That means:

🛠️ **You MUST use a null modem adapter** to swap TX and RX lines.

Otherwise, the device will not respond to commands.

## Project Structure

- `kunkin.py`: Core class to talk to the load
- `cli_control.py`: Interactive menu/monitoring tool

## Known Working Settings

- Baud rate: 9600
- Data bits: 8
- Parity: None
- Stop bits: 1
- Flow control: None
- Device address: 1

These must match the front panel settings on the KP184.

## Example

```
Mode: 1 | Load ON: True | Voltage: 12.03 V | Current: 1.20 A | Power: 14.44 W
```

Press `q` at any time to immediately disable the load.

---

## License

MIT License. Use at your own risk—especially when dumping 30A into a resistor.
```

---

Let me know your GitHub handle if you want a PR, or feel free to paste this in yourself. Want a `.gitignore` too?

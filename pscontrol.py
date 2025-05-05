import pyvisa as visa
import time
import numpy as np
import platform

rm = visa.ResourceManager()
ps = rm.open_resource("ASRL/dev/ttyUSB0::INSTR")
ps.baud_rate = 115200


def beep():
    if platform.system() == "Windows":
        import winsound
        winsound.MessageBeep()
    elif platform.system() == "Darwin":  # macOS
        import os
        os.system('say "beep"')
    else:  # Assume Linux/Unix
        import os
        os.system('echo -e "\a"')


def setpoints(i, e):
    current = f"{i:.4f}"[:6]
    volts = f"{e:.4f}"[:6]
    ps.write(f"CURR {current}")
    ps.write(f"VOLT {volts}")
    print(f'\rSet current to {current} Set voltage to {volts}', end='')


def kill():
    ps.write("CURR 0.0")
    ps.write("VOLT 0.0")


# Waveform parameters
amplitude = 0.5
offset = 0.5
frequency = 1
sampling_rate = 100  # points per unit of time
duration = 2 * np.pi  # one full sine cycle

# Generate time and waveform
t = np.linspace(0, duration, int(sampling_rate * duration))
half_sine_wave = amplitude * np.sin(frequency * t) + offset
delay = 60 / len(half_sine_wave)  # stretch waveform to ~60 seconds

# How many full cycles to repeat
times = 10000

try:
    while times > 0:
        for value in half_sine_wave:
            value = 0.0 if value < 0.01 else value
            setpoints(value, value + 0.05)
            time.sleep(delay)
        times -= 1
finally:
    beep()
    kill()

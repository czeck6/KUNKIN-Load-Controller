import pyvisa as visa
import time
import platform


class KiprimPS:
    def __init__(self, port="/dev/ttyUSB1", baudrate=115200):
        rm = visa.ResourceManager()
        self.ps = rm.open_resource(f"ASRL{port}::INSTR")
        self.ps.baud_rate = baudrate
        print(f"[INFO] Connected to Kiprim power supply on {port}")
        
    def is_output_on(self):
        state = self.ps.query("output?").strip().lower()
        return state == "on"
        
    def output_on(self):
        self.ps.write("output on")
        print("[DEBUG] Power supply output turned ON")

    def set_voltage(self, volts):
        val = f"{volts:.4f}"[:6]
        self.ps.write(f"VOLT {val}")
        print(f"[DEBUG] Voltage set to {val} V")

    def set_current(self, current):
        val = f"{current:.4f}"[:6]
        self.ps.write(f"CURR {val}")
        print(f"[DEBUG] Current set to {val} A")

    def output_off(self):
        """Turn off output and set voltage/current to 0.0 for safety"""
        self.ps.write("output off")
        self.ps.write("CURR 0.0")
        self.ps.write("VOLT 0.0")
        print("[DEBUG] Power supply output turned OFF and set to 0.0 V / 0.0 A")

    def beep(self):
        if platform.system() == "Windows":
            import winsound
            winsound.MessageBeep()
        elif platform.system() == "Darwin":
            import os
            os.system('say "beep"')
        else:
            import os
            os.system('echo -e "\a"')

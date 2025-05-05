import serial
import struct
import time


class KunkinDCLoad:
    """
    Class to control the KUNKIN 400W Programmable DC Load over RS232 using PySerial
    """

    # Register addresses
    REG_LOAD_ONOFF = 0x010E
    REG_LOAD_MODE = 0x0110
    REG_CV_SETTING = 0x0112
    REG_CC_SETTING = 0x0116
    REG_CR_SETTING = 0x011A
    REG_CW_SETTING = 0x011E
    REG_U_MEASURE = 0x0122
    REG_I_MEASURE = 0x0126

    # Load modes
    MODE_CV = 0  # Constant Voltage
    MODE_CC = 1  # Constant Current
    MODE_CR = 2  # Constant Resistance
    MODE_CW = 3  # Constant Power

    def __init__(self, port, address=1, baudrate=9600, timeout=1):
        self.address = address
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        print(f"[INFO] Connected to {port} (is_open={self.ser.is_open})")
        if not self.ser.is_open:
            self.ser.open()

    def __del__(self):
        if hasattr(self, "ser") and self.ser.is_open:
            self.ser.close()

    def calculate_crc(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return struct.pack("<H", crc)

    def send_command(self, cmd):
        print(f"[DEBUG] Sending: {cmd.hex(' ')}")
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.1)

        response = b''
        while self.ser.in_waiting:
            response += self.ser.read(self.ser.in_waiting)
            time.sleep(0.05)

        print(f"[DEBUG] Response: {response.hex(' ')}")
        return response

    def write_single_register(self, register, data_bytes):
        high_byte = (register >> 8) & 0xFF
        low_byte = register & 0xFF
        cmd = (
            bytes([
                self.address,
                0x06,
                high_byte,
                low_byte,
                0x00,
                0x01,
                0x04,
            ])
            + data_bytes
        )
        crc = self.calculate_crc(cmd)
        full_cmd = cmd + crc
        response = self.send_command(full_cmd)

        if response.startswith(cmd):
            return True
        return False

    def read_common_registers(self):
        cmd = bytes([
            self.address,
            0x03,
            0x03,
            0x00,
            0x00,
            0x00,
        ])
        cmd += self.calculate_crc(cmd)
        response = self.send_command(cmd)

        if len(response) < 6:
            return None

        if response[0] == self.address and response[1] == 0x03:
            data_len = response[2]
            data = response[3 : 3 + data_len]
            status_byte = data[0]
            is_on = (status_byte & 0x01) == 1
            mode = (status_byte >> 1) & 0x03
            voltage_bytes = data[2:5]
            current_bytes = data[5:8]
            voltage_mv = int.from_bytes(voltage_bytes, byteorder="big")
            current_ma = int.from_bytes(current_bytes, byteorder="big")
            return {
                "on": is_on,
                "mode": mode,
                "voltage_mv": voltage_mv,
                "voltage_v": voltage_mv / 1000.0,
                "current_ma": current_ma,
                "current_a": current_ma / 1000.0,
            }
        return None

    def set_power_state(self, on):
        value = 1 if on else 0
        data = struct.pack(">I", value)
        return self.write_single_register(self.REG_LOAD_ONOFF, data)

    def set_mode(self, mode):
        if mode not in [self.MODE_CV, self.MODE_CC, self.MODE_CR, self.MODE_CW]:
            raise ValueError("Invalid mode. Use 0 (CV), 1 (CC), 2 (CR), or 3 (CW)")
        data = struct.pack(">I", mode)
        return self.write_single_register(self.REG_LOAD_MODE, data)

    def set_voltage(self, voltage_v):
        voltage_mv = int(voltage_v * 1000)
        if not 0 <= voltage_mv <= 150000:
            raise ValueError("Voltage must be between 0 and 150V")
        data = struct.pack(">I", voltage_mv)
        return self.write_single_register(self.REG_CV_SETTING, data)

    def set_current(self, current_a):
        current_ma = int(current_a * 1000)
        if not 0 <= current_ma <= 30000:
            raise ValueError("Current must be between 0 and 30A")
        data = struct.pack(">I", current_ma)
        return self.write_single_register(self.REG_CC_SETTING, data)

    def set_resistance(self, resistance_ohm):
        resistance_mohm = int(resistance_ohm * 1000)
        if not 0 <= resistance_mohm <= 80000:
            raise ValueError("Resistance must be between 0 and 80 ohms")
        data = struct.pack(">I", resistance_mohm)
        return self.write_single_register(self.REG_CR_SETTING, data)

    def set_power(self, power_w):
        power_tenth_w = int(power_w * 10)
        if not 0 <= power_tenth_w <= 2500:
            raise ValueError("Power must be between 0 and 250W")
        data = struct.pack(">I", power_tenth_w)
        return self.write_single_register(self.REG_CW_SETTING, data)

    def get_measurements(self):
        data = self.read_common_registers()
        if data:
            return {
                "voltage_v": data["voltage_v"],
                "current_a": data["current_a"],
                "mode": data["mode"],
                "on": data["on"],
            }
        return None

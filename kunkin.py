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
        """
        Initialize the DC Load controller

        Args:
            port (str): COM port for RS232 connection
            address (int): Device address (default: 1)
            baudrate (int): Baud rate for serial communication (default: 9600)
            timeout (int): Serial timeout in seconds (default: 1)
        """
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
        """Close the serial port when object is destroyed"""
        if hasattr(self, "ser") and self.ser.is_open:
            self.ser.close()

    def calculate_crc(self, data):
        """
        Calculate CRC-16 (Modbus) checksum for the given data

        Args:
            data (bytes): Data to calculate CRC for

        Returns:
            bytes: CRC as bytes (low byte first, then high byte)
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return struct.pack("<H", crc)  # Little endian (low byte first)

    def send_command(self, cmd):
        print(f"[DEBUG] Sending: {cmd.hex(' ')}")  # Show outgoing command

        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.1)

        response = b''
        while self.ser.in_waiting:
            response += self.ser.read(self.ser.in_waiting)
            time.sleep(0.05)

        print(f"[DEBUG] Response: {response.hex(' ')}")  # Show raw response
        return response

    def write_single_register(self, register, data_bytes):
        """
        Write a single register with the given data

        Args:
            register (int): Register address
            data_bytes (bytes): 4 bytes of data to write

        Returns:
            bool: True if successful, False otherwise
        """
        # Prepare the command
        high_byte = (register >> 8) & 0xFF
        low_byte = register & 0xFF

        # Format: addr(1), func_code(1), reg_addr(2), num_reg(2), bytes_count(1), data(4), crc(2)
        cmd = (
            bytes(
                [
                    self.address,  # Equipment address
                    0x06,  # Function code for writing single register
                    high_byte,  # Register address high byte
                    low_byte,  # Register address low byte
                    0x00,
                    0x01,  # Number of registers (always 1)
                    0x04,  # Byte count (always 4)
                ]
            )
            + data_bytes
        )

        # Add CRC
        cmd += self.calculate_crc(cmd)

        # Send command and get response
        response = self.send_command(cmd)

        # Check if response matches command (for write operations)
        return response == cmd

    def read_common_registers(self):
        """
        Read all common data registers at once using special command

        Returns:
            dict: Dictionary with voltage, current, mode, and on/off status
        """
        # Special command to read common register bank
        cmd = bytes(
            [
                self.address,  # Equipment address
                0x03,  # Function code for reading registers
                0x03,
                0x00,  # Special address for common register bank
                0x00,
                0x00,  # Can be any value (not used)
            ]
        )

        # Add CRC
        cmd += self.calculate_crc(cmd)

        # Send command and get response
        response = self.send_command(cmd)

        # If response is too short, return None
        if len(response) < 6:
            return None

        # Parse response
        if response[0] == self.address and response[1] == 0x03:
            data_len = response[2]
            data = response[3 : 3 + data_len]

            # Extract values based on the manual:
            # D1.0 is ON/OFF bit, D1.1-D1.2 is mode bit
            status_byte = data[0]
            is_on = (status_byte & 0x01) == 1
            mode = (status_byte >> 1) & 0x03

            # D3-D5 is voltage value (mV), D6-D8 is current value (mA)
            # 3 bytes each with high byte first
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
        """
        Turn the load on or off

        Args:
            on (bool): True to turn on, False to turn off

        Returns:
            bool: True if successful, False otherwise
        """
        value = 1 if on else 0
        data = struct.pack(">I", value)  # 4 bytes, big endian
        return self.write_single_register(self.REG_LOAD_ONOFF, data)

    def set_mode(self, mode):
        """
        Set the load mode

        Args:
            mode (int): 0=CV, 1=CC, 2=CR, 3=CW

        Returns:
            bool: True if successful, False otherwise
        """
        if mode not in [self.MODE_CV, self.MODE_CC, self.MODE_CR, self.MODE_CW]:
            raise ValueError("Invalid mode. Use 0 (CV), 1 (CC), 2 (CR), or 3 (CW)")

        data = struct.pack(">I", mode)  # 4 bytes, big endian
        return self.write_single_register(self.REG_LOAD_MODE, data)

    def set_voltage(self, voltage_v):
        """
        Set the voltage in volts (CV mode)

        Args:
            voltage_v (float): Voltage in volts

        Returns:
            bool: True if successful, False otherwise
        """
        voltage_mv = int(voltage_v * 1000)  # Convert to mV
        if not 0 <= voltage_mv <= 150000:
            raise ValueError("Voltage must be between 0 and 150V")

        data = struct.pack(">I", voltage_mv)  # 4 bytes, big endian
        return self.write_single_register(self.REG_CV_SETTING, data)

    def set_current(self, current_a):
        """
        Set the current in amperes (CC mode)

        Args:
            current_a (float): Current in amperes

        Returns:
            bool: True if successful, False otherwise
        """
        current_ma = int(current_a * 1000)  # Convert to mA
        if not 0 <= current_ma <= 30000:
            raise ValueError("Current must be between 0 and 30A")

        data = struct.pack(">I", current_ma)  # 4 bytes, big endian
        return self.write_single_register(self.REG_CC_SETTING, data)

    def set_resistance(self, resistance_ohm):
        """
        Set the resistance in ohms (CR mode)

        Args:
            resistance_ohm (float): Resistance in ohms

        Returns:
            bool: True if successful, False otherwise
        """
        resistance_mohm = int(resistance_ohm * 1000)  # Convert to mOhm
        if not 0 <= resistance_mohm <= 80000:
            raise ValueError("Resistance must be between 0 and 80 ohms")

        data = struct.pack(">I", resistance_mohm)  # 4 bytes, big endian
        return self.write_single_register(self.REG_CR_SETTING, data)

    def set_power(self, power_w):
        """
        Set the power in watts (CW mode)

        Args:
            power_w (float): Power in watts

        Returns:
            bool: True if successful, False otherwise
        """
        power_tenth_w = int(power_w * 10)  # Convert to 0.1W units
        if not 0 <= power_tenth_w <= 2500:
            raise ValueError("Power must be between 0 and 250W")

        data = struct.pack(">I", power_tenth_w)  # 4 bytes, big endian
        return self.write_single_register(self.REG_CW_SETTING, data)

    def get_measurements(self):
        """
        Get the current measurements from the device

        Returns:
            dict: Dictionary with measured voltage and current values
        """
        data = self.read_common_registers()
        if data:
            return {
                "voltage_v": data["voltage_v"],
                "current_a": data["current_a"],
                "mode": data["mode"],
                "on": data["on"],
            }
        return None


# Example usage
if __name__ == "__main__":
    import time

    # Replace 'COM1' with your actual serial port
    load = KunkinDCLoad(port="COM5")

    # Set to CC mode
    load.set_mode(KunkinDCLoad.MODE_CC)

    # Set current to 1A
    load.set_current(1.0)

    # Turn on the load
    load.set_power_state(True)

    # Read and print measurements every second for 5 seconds
    for _ in range(5):
        measurements = load.get_measurements()
        print(
            f"Voltage: {measurements['voltage_v']:.3f}V, Current: {measurements['current_a']:.3f}A"
        )
        time.sleep(1)

    # Turn off the load
    load.set_power_state(False)

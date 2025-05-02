import sys
import threading
import time

from kunkin import KunkinDCLoad  # Ensure your KunkinDCLoad class is saved in kunkin.py


# Cross-platform getch()
if sys.platform.startswith('win'):
    import msvcrt

    def getch():
        return msvcrt.getch().decode('utf-8')

else:
    import termios
    import tty

    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def monitor_load(load, stop_event):
    """Poll and display load status"""
    while not stop_event.is_set():
        data = load.get_measurements()
        if data:
            watts = data["voltage_v"] * data["current_a"]
            print(f"\rMode: {data['mode']} | Load ON: {data['on']} | "
                  f"Voltage: {data['voltage_v']:.2f} V | "
                  f"Current: {data['current_a']:.2f} A | "
                  f"Power: {watts:.2f} W   ", end="")
        time.sleep(1)


def emergency_watchdog(load, stop_event):
    """Listen for 'q' to immediately turn off the load"""
    while not stop_event.is_set():
        ch = getch()
        if ch.lower() == 'q':
            print("\n[!] EMERGENCY SHUTDOWN ACTIVATED")
            load.set_power_state(False)
            stop_event.set()
            break


def show_menu():
    print("\n=== KUNKIN LOAD CONTROL MENU ===")
    print("1. Set mode (0=CV, 1=CC, 2=CR, 3=CW)")
    print("2. Set voltage (V)")
    print("3. Set current (A)")
    print("4. Set resistance (Ohm)")
    print("5. Set power (W)")
    print("6. Turn load ON")
    print("7. Turn load OFF")
    print("8. Start monitoring")
    print("9. Exit")
    print("Press 'q' anytime to kill the load.\n")


def main():
    import os

    port = input("Enter serial port (e.g., COM5 or /dev/ttyUSB0): ").strip()
    load = KunkinDCLoad(port=port)

    stop_event = threading.Event()
    monitor_thread = None

    print("\n[Info] Press 'q' at any time to shut off the load and exit.\n")

    try:
        while not stop_event.is_set():
            # On Windows, use non-blocking key detection
            if sys.platform.startswith('win') and msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'q':
                    print("\n[!] Emergency shutdown.")
                    load.set_power_state(False)
                    break

            show_menu()
            choice = input("Select an option: ").strip()

            if choice == '1':
                mode = int(input("Enter mode (0=CV, 1=CC, 2=CR, 3=CW): "))
                load.set_mode(mode)
            elif choice == '2':
                v = float(input("Enter voltage (V): "))
                load.set_voltage(v)
            elif choice == '3':
                c = float(input("Enter current (A): "))
                load.set_current(c)
            elif choice == '4':
                r = float(input("Enter resistance (Ohm): "))
                load.set_resistance(r)
            elif choice == '5':
                w = float(input("Enter power (W): "))
                load.set_power(w)
            elif choice == '6':
                load.set_power_state(True)
            elif choice == '7':
                load.set_power_state(False)
            elif choice == '8':
                if monitor_thread and monitor_thread.is_alive():
                    print("Monitoring already running.")
                else:
                    print("Starting live monitoring. Press 'q' to stop.")
                    monitor_thread = threading.Thread(target=monitor_load, args=(load, stop_event), daemon=True)
                    monitor_thread.start()
            elif choice == '9':
                stop_event.set()
                load.set_power_state(False)
            else:
                print("Invalid option.")

            time.sleep(0.1)  # Avoid CPU hammering
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C pressed. Turning off load and exiting.")
    finally:
        stop_event.set()
        load.set_power_state(False)
        print("Goodbye.")


if __name__ == "__main__":
    main()

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static, Input
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer

from kunkin import KunkinDCLoad
from kiprim import KiprimPS

class DeviceStatus(Static):
    """Widget to display live data for either Load or PS."""
    def update_content(self, label, data):
        self.update(f"[b]{label}[/b]\n" + "\n".join(data))

class ControlPanel(App):
    CSS_PATH = "dashboard.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    current_mode = reactive(1)  # Default to CC mode

    def __init__(self, load_port="/dev/ttyUSB0", ps_port="/dev/ttyUSB1"):
        super().__init__()
        self.load = KunkinDCLoad(port=load_port)
        self.ps = KiprimPS(port=ps_port)
        self.timer: Timer | None = None
        self.ps_status = DeviceStatus()
        self.load_status = DeviceStatus()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield self.ps_status
            yield self.load_status
        with Horizontal():
            with Vertical():
                yield Input(placeholder="Set PS Voltage (V)...", id="ps_voltage")
                yield Input(placeholder="Set PS Current (A)...", id="ps_current")
                yield Button("PS ON", id="ps_on")
                yield Button("PS OFF", id="ps_off")
            with Vertical():
                self.load_voltage_input = Input(placeholder="Set Load Voltage (V)...", id="load_voltage")
                self.load_current_input = Input(placeholder="Set Load Current (A)...", id="load_current")
                self.load_resistance_input = Input(placeholder="Set Load Resistance (Ohm)...", id="load_resistance")
                self.load_power_input = Input(placeholder="Set Load Power (W)...", id="load_power")
                self.load_mode_input = Input(placeholder="Set Load Mode (0=CV, 1=CC, 2=CR, 3=CW)...", id="load_mode")
                yield self.load_voltage_input
                yield self.load_current_input
                yield self.load_resistance_input
                yield self.load_power_input
                yield self.load_mode_input
                yield Button("LOAD ON", id="load_on")
                yield Button("LOAD OFF", id="load_off")
        yield Footer()

    def on_mount(self) -> None:
        self.timer = self.set_interval(1.0, self.refresh_status)
        self.update_load_inputs()
        self.refresh_status()

    def refresh_status(self):
        try:
            ps_v = float(self.ps.ps.query("measure:voltage?").strip())
            ps_c = float(self.ps.ps.query("measure:current?").strip())
        except Exception:
            ps_v = ps_c = 0.0

        self.ps_status.update_content("Power Supply", [
            f"Voltage: {ps_v:.2f} V",
            f"Current: {ps_c:.2f} A"
        ])

        try:
            load_data = self.load.get_measurements()
            if load_data:
                self.current_mode = load_data["mode"]
                self.load_status.update_content("Kunkin Load", [
                    f"Mode: {load_data['mode']}",
                    f"ON: {load_data['on']}",
                    f"Voltage: {load_data['voltage_v']:.2f} V",
                    f"Current: {load_data['current_a']:.2f} A",
                    f"Power: {load_data['voltage_v'] * load_data['current_a']:.2f} W"
                ])
            else:
                self.load_status.update_content("Kunkin Load", ["No response"])
        except Exception:
            self.load_status.update_content("Kunkin Load", ["Error reading load"])

        self.update_load_inputs()

    def update_load_inputs(self):
        self.load_voltage_input.display = self.current_mode == 0
        self.load_current_input.display = self.current_mode == 1
        self.load_resistance_input.display = self.current_mode == 2
        self.load_power_input.display = self.current_mode == 3

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "ps_on":
                self.ps.output_on()
            case "ps_off":
                self.ps.output_off()
            case "load_on":
                self.load.set_power_state(True)
            case "load_off":
                self.load.set_power_state(False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        match event.input.id:
            case "ps_voltage":
                try:
                    self.ps.set_voltage(float(event.value))
                except ValueError:
                    pass
            case "ps_current":
                try:
                    self.ps.set_current(float(event.value))
                except ValueError:
                    pass
            case "load_voltage":
                try:
                    self.load.set_voltage(float(event.value))
                except ValueError:
                    pass
            case "load_current":
                try:
                    self.load.set_current(float(event.value))
                except ValueError:
                    pass
            case "load_resistance":
                try:
                    self.load.set_resistance(float(event.value))
                except ValueError:
                    pass
            case "load_power":
                try:
                    self.load.set_power(float(event.value))
                except ValueError:
                    pass
            case "load_mode":
                try:
                    self.current_mode = int(event.value)
                    self.load.set_mode(self.current_mode)
                    self.update_load_inputs()
                except ValueError:
                    pass
        event.input.value = ""
        self.refresh_status()

    def on_exit(self) -> None:
        self.load.set_power_state(False)
        self.ps.output_off()

if __name__ == "__main__":
    ControlPanel().run()

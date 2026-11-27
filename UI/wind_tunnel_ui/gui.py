"""PySide6 desktop GUI. No FluidNC commands or sensor packet formats here."""
import queue
import sys
from concurrent.futures import ThreadPoolExecutor
from machine_settings import X_MIN, X_MAX, Z_MIN, Z_MAX, INITIAL_FEED

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QLineEdit, QDoubleSpinBox,
    QSpinBox, QTabWidget, QCheckBox, QPlainTextEdit, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QMessageBox,
)
import pyqtgraph as pg

from backend import WindTunnelController, ScanPlan, MachineLimits


STYLE = """
QWidget { background: #111827; color: #e5e7eb; font: 10pt 'Segoe UI'; }
QMainWindow { background: #0b1220; }
QGroupBox { border: 1px solid #374151; border-radius: 11px; margin-top: 12px;
            padding: 12px 10px 10px; font-weight: 600; background: #1f2937; }
QGroupBox::title { subcontrol-origin: margin; left: 13px; padding: 0 6px; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 6px;
    selection-background-color: #2563eb; min-height: 22px;
}
QPushButton { background: #2563eb; border: none; border-radius: 7px; padding: 9px 13px;
              font-weight: 600; }
QPushButton:hover { background: #1d4ed8; }
QPushButton:disabled { background: #374151; color: #94a3b8; }
QPushButton#danger { background: #b91c1c; }
QPushButton#danger:hover { background: #991b1b; }
QPushButton#soft { background: #334155; }
QPushButton#soft:hover { background: #475569; }
QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; }
QTabBar::tab { background: #1f2937; padding: 10px 18px; border-radius: 6px; margin-right: 4px; }
QTabBar::tab:selected { background: #2563eb; }
QPlainTextEdit, QTableWidget { background: #0f172a; border: 1px solid #374151;
                               border-radius: 6px; }
QHeaderView::section { background: #1f2937; border: 0; padding: 5px; }
QProgressBar { border: 1px solid #475569; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #0d9488; }
"""


def spin(low, high, value, decimals=1, suffix=""):
    w = QDoubleSpinBox()
    w.setRange(low, high)
    w.setDecimals(decimals)
    w.setValue(value)
    w.setSuffix(suffix)
    return w


def button(text, callback, kind=""):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    b.clicked.connect(callback)
    return b


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wind Tunnel Control — FluidNC")
        self.resize(1150, 780)
        self.events = queue.Queue()
        self.controller = WindTunnelController(self.enqueue, limits=MachineLimits(X_MIN, X_MAX, Z_MIN, Z_MAX))
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.busy = False
        self.connected = False
        self.homed = False
        self.sensor_active = False
        self.velocities = []
        self.times = []
        self.measurements = 0
        self._build()
        self.refresh_ports()
        self.change_mode()
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.process_events)
        self.clock.start(100)
        self.log("Simulation mode is available without any hardware.")
        self.log("Hardware setup must be verified before arming movement.")

    def enqueue(self, kind, data):
        self.events.put((kind, data))

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("WIND TUNNEL  /  CONTROL CENTER")
        title.setStyleSheet("font-size: 19pt; font-weight: 700; letter-spacing: 1px;")
        top.addWidget(title)
        top.addStretch()
        self.status = QLabel("● DISCONNECTED")
        self.status.setStyleSheet("color: #f59e0b; font-weight: 700;")
        top.addWidget(self.status)
        outer.addLayout(top)

        connection = QGroupBox("Connection and operating mode")
        controls = QGridLayout(connection)
        self.mode = QComboBox()
        self.mode.addItems(["Simulation", "FluidNC movement only", "FluidNC + ESP32-C3"])
        self.mode.currentIndexChanged.connect(self.change_mode)
        controls.addWidget(QLabel("Backend"), 0, 0)
        controls.addWidget(self.mode, 0, 1)
        self.motion_port = QComboBox()
        self.motion_port.setEditable(True)
        self.sensor_port = QComboBox()
        self.sensor_port.setEditable(True)
        controls.addWidget(QLabel("FluidNC USB port"), 0, 2)
        controls.addWidget(self.motion_port, 0, 3)
        controls.addWidget(QLabel("Sensor USB port"), 1, 2)
        controls.addWidget(self.sensor_port, 1, 3)
        self.refresh = button("Refresh ports", self.refresh_ports, "soft")
        controls.addWidget(self.refresh, 0, 4)
        self.connect_btn = button("Connect", self.connect_backend)
        controls.addWidget(self.connect_btn, 1, 4)
        self.arm = QCheckBox("Hardware checked: wiring, homing switches, machine limits and physical stop verified")
        self.arm.setStyleSheet("color: #fdba74;")
        controls.addWidget(self.arm, 1, 0, 1, 2)
        outer.addWidget(connection)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.make_motion_tab(), "Motion control")
        self.tabs.addTab(self.make_scan_tab(), "Automatic scan")
        self.tabs.addTab(self.make_results_tab(), "Live results")
        outer.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.activity = QLabel("Ready")
        self.activity.setStyleSheet("color: #93c5fd;")
        bottom.addWidget(self.activity)
        bottom.addStretch()
        bottom.addWidget(QLabel("For physical emergencies, use the independent hardware stop."))
        outer.addLayout(bottom)

    def make_motion_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        position = QGroupBox("Current machine position (reported / simulated)")
        row = QHBoxLayout(position)
        self.current_x = QLabel("— mm")
        self.current_z = QLabel("— mm")
        for title, label in [("X", self.current_x), ("Z", self.current_z)]:
            col = QVBoxLayout()
            col.addWidget(QLabel(title + " position"))
            label.setStyleSheet("font-size: 24pt; font-weight: 700; color: #5eead4;")
            col.addWidget(label)
            row.addLayout(col)
        layout.addWidget(position)

        box = QGroupBox("Manual movement — physical X and Z coordinates")
        form = QFormLayout(box)
        self.target_x = spin(self.controller.limits.x_min, self.controller.limits.x_max, self.controller.limits.x_min, 1, " mm")
        self.target_z = spin(self.controller.limits.z_min, self.controller.limits.z_max, self.controller.limits.z_min, 1, " mm")
        self.feed = spin(1, 12400, INITIAL_FEED, 0, " mm/min")
        form.addRow("Target X", self.target_x)
        form.addRow("Target Z", self.target_z)
        form.addRow("Feed rate", self.feed)
        layout.addWidget(box)

        actions = QHBoxLayout()
        self.home_btn = button("HOME / reference", lambda: self.run_task("Home", self.controller.home))
        self.move_btn = button("Move to target", lambda: self.run_task("Move", self.controller.move_to,
                                                 self.target_x.value(), self.target_z.value(), self.feed.value()))
        self.measure_btn = button("Read sensor", lambda: self.run_task("Read", self.controller.read_once))
        self.status_btn = button("Refresh status", lambda: self.run_task("Status", self.controller.refresh_status), "soft")
        self.hold_btn = button("SOFTWARE HOLD / STOP SCAN", self.hold, "danger")
        for widget in (self.home_btn, self.move_btn, self.measure_btn, self.status_btn, self.hold_btn):
            actions.addWidget(widget)
        layout.addLayout(actions)
        note = QLabel("FluidNC uses logical X/Y: X represents traverser X, Y represents traverser Z. CoreXY coupling belongs in config.yaml.\n"
                      "Real movement remains locked until you connect, arm, and home. Software hold is NOT an emergency stop.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #fbbf24;")
        layout.addWidget(note)
        layout.addStretch()
        return page

    def make_scan_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        box = QGroupBox("Scan grid (serpentine order)")
        grid = QGridLayout(box)
        self.x_start = spin(self.controller.limits.x_min, self.controller.limits.x_max, self.controller.limits.x_min, 1, " mm")
        self.x_end = spin(self.controller.limits.x_min, self.controller.limits.x_max, min(self.controller.limits.x_min+5, self.controller.limits.x_max), 1, " mm")
        self.z_start = spin(self.controller.limits.z_min, self.controller.limits.z_max, self.controller.limits.z_min, 1, " mm")
        self.z_end = spin(self.controller.limits.z_min, self.controller.limits.z_max, min(self.controller.limits.z_min+5, self.controller.limits.z_max), 1, " mm")
        self.nx = QSpinBox(); self.nx.setRange(2,51); self.nx.setValue(2)
        self.nz = QSpinBox(); self.nz.setRange(2,51); self.nz.setValue(2)
        self.settle = spin(0,120,2,1," s")
        self.samples = QSpinBox(); self.samples.setRange(1,100); self.samples.setValue(5)
        fields = [("X start", self.x_start), ("X end", self.x_end), ("Z start", self.z_start),
                  ("Z end", self.z_end), ("X points", self.nx), ("Z points", self.nz),
                  ("Settle", self.settle), ("Samples / point", self.samples)]
        for index, (label, entry) in enumerate(fields):
            col = (index // 4) * 2
            row = index % 4
            grid.addWidget(QLabel(label), row, col)
            grid.addWidget(entry, row, col+1)
        layout.addWidget(box)
        self.point_count = QLabel("4 points")
        for ctrl in (self.nx, self.nz):
            ctrl.valueChanged.connect(lambda: self.point_count.setText(f"{self.nx.value()*self.nz.value()} points"))
        layout.addWidget(self.point_count)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        buttons = QHBoxLayout()
        self.scan_btn = button("START AUTOMATIC SCAN", self.start_scan)
        buttons.addWidget(self.scan_btn)
        buttons.addWidget(button("SOFTWARE HOLD / STOP", self.hold, "danger"))
        layout.addLayout(buttons)
        self.output = QLabel("Results will be saved as timestamped CSV files under measurements/.")
        self.output.setWordWrap(True)
        layout.addWidget(self.output)
        layout.addStretch()
        return page

    def make_results_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        summary = QHBoxLayout()
        self.speed_label = QLabel("— m/s")
        self.pressure_label = QLabel("— Pa")
        self.temp_label = QLabel("— °C")
        for title, label in [("Air velocity", self.speed_label), ("Pressure", self.pressure_label),
                             ("Temperature", self.temp_label)]:
            box = QGroupBox(title)
            inner = QVBoxLayout(box)
            label.setStyleSheet("font-size: 21pt; color: #5eead4; font-weight: 700;")
            inner.addWidget(label)
            summary.addWidget(box)
        layout.addLayout(summary)
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget(background="#0f172a")
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        self.plot.setLabel("left", "Velocity", units="m/s")
        self.plot.setLabel("bottom", "Measurement index")
        self.line = self.plot.plot([], [], pen=pg.mkPen("#2dd4bf", width=2), symbol="o", symbolSize=4)
        layout.addWidget(self.plot, 1)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time (UTC)", "X (mm)", "Z (mm)", "Speed (m/s)", "Pressure (Pa)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        log_box = QGroupBox("Event log")
        inner = QVBoxLayout(log_box)
        self.logbox = QPlainTextEdit()
        self.logbox.setReadOnly(True)
        self.logbox.setMaximumHeight(120)
        inner.addWidget(self.logbox)
        layout.addWidget(log_box)
        return page

    def change_mode(self):
        if not hasattr(self, "motion_port"):
            return
        hardware = self.mode.currentText() != "Simulation"
        self.motion_port.setEnabled(hardware)
        self.sensor_port.setEnabled(self.mode.currentText() == "FluidNC + ESP32-C3")
        self.arm.setEnabled(hardware)
        self.arm.setChecked(False)
        self.update_controls()

    def refresh_ports(self):
        try:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports()]
        except ImportError:
            ports = []
        for dropdown in (self.motion_port, self.sensor_port):
            old = dropdown.currentText()
            dropdown.clear()
            dropdown.addItem("")
            dropdown.addItems(ports)
            dropdown.setCurrentText(old)

    def connect_backend(self):
        if self.connected:
            self.run_task("Disconnect", self.controller.disconnect)
        else:
            self.run_task("Connect", self.controller.connect, self.mode.currentText(),
                          self.motion_port.currentText().strip(), self.sensor_port.currentText().strip())

    def is_armed(self):
        if self.mode.currentText() == "Simulation":
            return True
        if not self.arm.isChecked():
            QMessageBox.warning(self, "Hardware not armed", "Verify electrical wiring, CoreXY orientation, limit switches, travel limits, homing direction and physical stop before enabling movement.")
            return False
        return True

    def run_task(self, name, operation, *args):
        if self.busy:
            return
        if name in ("Home", "Move", "Scan") and not self.is_armed():
            return
        self.busy = True
        self.activity.setText(name + " ...")
        self.update_controls()

        def worker():
            try:
                operation(*args)
            except Exception as exc:
                self.enqueue("error", f"{name}: {exc}")
            finally:
                self.enqueue("task_done", name)

        self.executor.submit(worker)

    def start_scan(self):
        plan = ScanPlan(self.x_start.value(), self.x_end.value(), self.z_start.value(),
                        self.z_end.value(), self.nx.value(), self.nz.value(),
                        self.settle.value(), self.samples.value(), self.feed.value())
        self.run_task("Scan", self.controller.run_scan, plan)

    def hold(self):
        if not self.connected:
            return
        self.controller.request_hold()
        self.homed = False
        self.update_controls()
        self.log("Software HOLD requested. Verify machine state; use physical stop for emergencies.")

    def update_controls(self):
        if not hasattr(self, "home_btn"):
            return
        available = self.connected and not self.busy
        self.connect_btn.setText("Disconnect" if self.connected else "Connect")
        self.connect_btn.setEnabled(not self.busy)
        self.mode.setEnabled(not self.connected and not self.busy)
        self.motion_port.setEnabled(not self.connected and not self.busy and self.mode.currentText() != "Simulation")
        self.sensor_port.setEnabled(not self.connected and not self.busy and self.mode.currentText() == "FluidNC + ESP32-C3")
        dry = self.mode.currentText() == "FluidNC movement only"
        self.samples.setEnabled(not dry and not self.busy)
        self.scan_btn.setText("START MOVEMENT-ONLY GRID TEST" if dry else "START AUTOMATIC SCAN")
        self.arm.setEnabled(not self.busy and self.mode.currentText() != "Simulation")
        self.home_btn.setEnabled(available)
        self.move_btn.setEnabled(available and self.homed)
        self.scan_btn.setEnabled(available and self.homed)
        self.measure_btn.setEnabled(available and self.sensor_active)
        self.status_btn.setEnabled(available)
        self.hold_btn.setEnabled(self.connected)

    def process_events(self):
        while True:
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "connected":
                self.connected = True
                self.homed = False
                self.sensor_active = data["sensor"]
                self.arm.setChecked(False)
                self.current_x.setText("— mm")
                self.current_z.setText("— mm")
                self.speed_label.setText("— m/s")
                self.pressure_label.setText("— Pa")
                self.temp_label.setText("— °C")
                self.measurements = 0
                self.times.clear(); self.velocities.clear()
                self.line.setData([], [])
                self.table.setRowCount(0)
                self.output.setText("Movement-only: no sensor data or CSV will be created." if not self.sensor_active else "Results saved under measurements/.")
                self.status.setText("● CONNECTED  /  " + data["mode"])
                self.status.setStyleSheet("color: #34d399; font-weight: 700;")
                self.log("Connected to " + data["mode"] + (" (sensor active)" if data["sensor"] else " (no sensor)"))
            elif kind == "disconnected":
                self.connected = False
                self.homed = False
                self.sensor_active = False
                self.arm.setChecked(False)
                self.status.setText("● DISCONNECTED")
                self.status.setStyleSheet("color: #f59e0b; font-weight: 700;")
            elif kind == "position":
                self.current_x.setText(f"{data.x_mm:.2f} mm")
                self.current_z.setText(f"{data.z_mm:.2f} mm")
            elif kind == "activity":
                self.activity.setText(str(data))
                if data == "Ready":
                    self.homed = bool(self.controller.homed)
            elif kind == "scan_progress":
                self.progress.setMaximum(data["total"])
                self.progress.setValue(data["done"])
            elif kind == "scan_finished":
                self.output.setText(f"Saved {data['count']} points to {data['path']}")
                self.log("Scan complete: " + data["path"])
            elif kind == "dry_scan_finished":
                self.output.setText(f"Completed {data['count']} movement-only points. No sensor data saved.")
                self.log("Movement-only grid test complete.")
            elif kind == "measurement":
                self.record_measurement(data["reading"], data["position"])
            elif kind == "machine_status":
                self.log("FluidNC / simulator status: " + data.state)
                if not self.controller.homed:
                    self.homed = False
            elif kind == "error":
                self.log("ERROR: " + str(data))
                self.activity.setText("ERROR — " + str(data))
                self.status.setStyleSheet("color: #fca5a5; font-weight: 700;")
            elif kind == "task_done":
                self.busy = False
                self.homed = bool(self.controller.homed)
                self.update_controls()
            self.update_controls()

    def record_measurement(self, reading, position):
        self.measurements += 1
        self.speed_label.setText(f"{reading.speed_ms:.2f} m/s")
        self.pressure_label.setText("— Pa" if reading.pressure_pa is None else f"{reading.pressure_pa:.1f} Pa")
        self.temp_label.setText("— °C" if reading.temperature_c is None else f"{reading.temperature_c:.1f} °C")
        self.times.append(self.measurements)
        self.velocities.append(reading.speed_ms)
        self.line.setData(self.times[-250:], self.velocities[-250:])
        n = self.table.rowCount()
        self.table.insertRow(n)
        timestamp = reading.timestamp[11:19]
        row = [timestamp,
               "—" if position is None else f"{position.x_mm:.1f}",
               "—" if position is None else f"{position.z_mm:.1f}",
               f"{reading.speed_ms:.2f}",
               "—" if reading.pressure_pa is None else f"{reading.pressure_pa:.1f}"]
        for col, value in enumerate(row):
            self.table.setItem(n, col, QTableWidgetItem(value))
        self.table.scrollToBottom()

    def log(self, message):
        self.logbox.appendPlainText(str(message))

    def closeEvent(self, event):
        if self.busy:
            QMessageBox.warning(self, "Operation active", "Stop the scan or wait for the current operation to finish before closing.")
            event.ignore()
            return
        try:
            self.controller.disconnect()
        finally:
            self.executor.shutdown(wait=False, cancel_futures=True)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Realtime two-IMU visualizer for the Arduino wit_c_sdk_iic example."""

from __future__ import annotations

import argparse
import json
import math
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Iterable, Optional, Tuple

try:
    import matplotlib.pyplot as plt
    import numpy as np
    import serial
    from matplotlib.animation import FuncAnimation
    from matplotlib.gridspec import GridSpec
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from serial.tools import list_ports
except ImportError as exc:
    print("Missing dependency:", exc)
    print("Install with: python -m pip install pyserial numpy matplotlib")
    raise SystemExit(1)


LINE_RE = re.compile(
    r"sensor(?P<index>\d+)\[0x(?P<addr>[0-9a-fA-F]+)\]\s+"
    r"(?P<kind>acc|gyro|angle):"
    r"(?P<x>[-+]?\d+(?:\.\d+)?)\s+"
    r"(?P<y>[-+]?\d+(?:\.\d+)?)\s+"
    r"(?P<z>[-+]?\d+(?:\.\d+)?)"
)
COLORS = {"sensor1": "tab:orange", "sensor2": "tab:cyan"}


@dataclass
class AngleCalibration:
    bias_deg: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))
    matrix: np.ndarray = field(default_factory=lambda: np.eye(3))

    @classmethod
    def from_dict(cls, data: Dict) -> "AngleCalibration":
        return cls(
            bias_deg=np.array(data.get("bias_deg", [0.0, 0.0, 0.0]), dtype=float),
            scale=np.array(data.get("scale", [1.0, 1.0, 1.0]), dtype=float),
            matrix=np.array(data.get("matrix", np.eye(3).tolist()), dtype=float),
        )

    def apply(self, raw_deg: np.ndarray) -> np.ndarray:
        return self.matrix @ ((raw_deg - self.bias_deg) * self.scale)


@dataclass
class SensorState:
    key: str
    label: str
    address: str = ""
    acc: np.ndarray = field(default_factory=lambda: np.zeros(3))
    gyro: np.ndarray = field(default_factory=lambda: np.zeros(3))
    raw_angle_deg: np.ndarray = field(default_factory=lambda: np.zeros(3))
    angle_deg: np.ndarray = field(default_factory=lambda: np.zeros(3))
    last_update: float = 0.0
    calibration: AngleCalibration = field(default_factory=AngleCalibration)
    angle_history: Deque[Tuple[float, np.ndarray]] = field(default_factory=lambda: deque(maxlen=240))
    trace_history: Deque[np.ndarray] = field(default_factory=lambda: deque(maxlen=160))
    parsed_count: int = 0


@dataclass
class SerialEvent:
    line: str = ""
    parsed: Optional[Tuple[str, str, str, np.ndarray]] = None
    error: str = ""


def load_config(path: Optional[Path]) -> Dict:
    if not path:
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_sensor_states(config: Dict) -> Dict[str, SensorState]:
    sensors = {}
    config_sensors = config.get("sensors", {})
    for key in ("sensor1", "sensor2"):
        sensor_cfg = config_sensors.get(key, {})
        sensors[key] = SensorState(
            key=key,
            label=sensor_cfg.get("label", key.upper()),
            address=sensor_cfg.get("address", ""),
            calibration=AngleCalibration.from_dict(sensor_cfg.get("angle", {})),
        )
    return sensors


def list_serial_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")


def parse_line(line: str) -> Optional[Tuple[str, str, str, np.ndarray]]:
    match = LINE_RE.search(line)
    if not match:
        return None
    key = f"sensor{match.group('index')}"
    address = "0x" + match.group("addr").upper()
    kind = match.group("kind")
    values = np.array(
        [float(match.group("x")), float(match.group("y")), float(match.group("z"))],
        dtype=float,
    )
    return key, address, kind, values


def serial_reader(port: str, baudrate: int, out_queue: "queue.Queue[SerialEvent]", stop_event: threading.Event) -> None:
    try:
        with serial.Serial(port, baudrate=baudrate, timeout=0.2) as ser:
            ser.reset_input_buffer()
            while not stop_event.is_set():
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                out_queue.put(SerialEvent(line=line, parsed=parse_line(line)))
    except serial.SerialException as exc:
        out_queue.put(SerialEvent(error=f"Serial error: {exc}"))
        stop_event.set()


def rotation_matrix_from_rpy_deg(rpy_deg: Iterable[float]) -> np.ndarray:
    roll, pitch, yaw = np.deg2rad(np.array(list(rpy_deg), dtype=float))
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def cuboid_faces(center: np.ndarray, size: Tuple[float, float, float], rot: np.ndarray):
    sx, sy, sz = np.array(size, dtype=float) / 2.0
    corners = np.array(
        [
            [-sx, -sy, -sz],
            [sx, -sy, -sz],
            [sx, sy, -sz],
            [-sx, sy, -sz],
            [-sx, -sy, sz],
            [sx, -sy, sz],
            [sx, sy, sz],
            [-sx, sy, sz],
        ]
    )
    corners = corners @ rot.T + center
    return [
        [corners[i] for i in [0, 1, 2, 3]],
        [corners[i] for i in [4, 5, 6, 7]],
        [corners[i] for i in [0, 1, 5, 4]],
        [corners[i] for i in [2, 3, 7, 6]],
        [corners[i] for i in [1, 2, 6, 5]],
        [corners[i] for i in [0, 3, 7, 4]],
    ]


def draw_sensor(ax, state: SensorState, center: np.ndarray, color: str) -> None:
    rot = rotation_matrix_from_rpy_deg(state.angle_deg)
    body = Poly3DCollection(cuboid_faces(center, (1.2, 0.7, 0.22), rot), alpha=0.45, facecolor=color, edgecolor="black")
    ax.add_collection3d(body)

    for label, vec, axis_color in (
        ("X", np.array([1.0, 0.0, 0.0]), "red"),
        ("Y", np.array([0.0, 1.0, 0.0]), "green"),
        ("Z", np.array([0.0, 0.0, 1.0]), "blue"),
    ):
        tip = center + rot @ vec
        ax.plot([center[0], tip[0]], [center[1], tip[1]], [center[2], tip[2]], color=axis_color, linewidth=2)
        ax.text(tip[0], tip[1], tip[2], label, color=axis_color)

    front_tip = center + rot @ np.array([1.2, 0.0, 0.0])
    if not state.trace_history or np.linalg.norm(state.trace_history[-1] - front_tip) > 0.02:
        state.trace_history.append(front_tip)
    if len(state.trace_history) > 1:
        trace = np.array(state.trace_history)
        ax.plot(trace[:, 0], trace[:, 1], trace[:, 2], color=color, linewidth=2, alpha=0.85)

    age = time.time() - state.last_update if state.last_update else float("inf")
    status = "live" if age < 2.0 else "waiting"
    roll, pitch, yaw = state.angle_deg
    ax.text(
        center[0] - 1.1,
        center[1] - 1.0,
        center[2] + 1.2,
        f"{state.label} {state.address} {status}\nR:{roll:6.1f} P:{pitch:6.1f} Y:{yaw:6.1f}",
        fontsize=9,
    )


def update_states(in_queue: "queue.Queue[SerialEvent]", sensors: Dict[str, SensorState], raw_lines: Deque[str]) -> Optional[str]:
    latest_error = None
    while True:
        try:
            event = in_queue.get_nowait()
        except queue.Empty:
            return latest_error

        if event.error:
            latest_error = event.error
            raw_lines.append(event.error)
            continue
        if event.line:
            raw_lines.append(event.line)
        if not event.parsed:
            continue

        key, address, kind, values = event.parsed
        if key not in sensors:
            continue
        state = sensors[key]
        state.address = address
        state.parsed_count += 1
        state.last_update = time.time()
        if kind == "acc":
            state.acc = values
        elif kind == "gyro":
            state.gyro = values
        elif kind == "angle":
            state.raw_angle_deg = values
            state.angle_deg = state.calibration.apply(values)
            state.angle_history.append((time.time(), state.angle_deg.copy()))


def draw_angle_history(ax, sensors: Dict[str, SensorState]) -> None:
    ax.set_title("Angle History")
    ax.set_xlabel("seconds")
    ax.set_ylabel("degrees")
    ax.grid(True, alpha=0.25)
    now = time.time()
    labels = ("roll", "pitch", "yaw")
    linestyles = ("-", "--", ":")
    for key, state in sensors.items():
        if len(state.angle_history) < 2:
            continue
        hist = list(state.angle_history)
        ts = np.array([item[0] - now for item in hist])
        values = np.array([item[1] for item in hist])
        for axis in range(3):
            ax.plot(
                ts,
                values[:, axis],
                color=COLORS.get(key, "black"),
                linestyle=linestyles[axis],
                linewidth=1.4,
                label=f"{state.label} {labels[axis]}",
            )
    ax.set_xlim(-60, 1)
    ax.set_ylim(-190, 190)
    ax.legend(loc="upper left", fontsize=8, ncol=2)


def draw_data_panel(ax, sensors: Dict[str, SensorState], raw_lines: Deque[str], port: str, baudrate: int, error: Optional[str]) -> None:
    ax.axis("off")
    lines = [f"Serial: {port} @ {baudrate}", ""]
    if error:
        lines.extend([error, "Close Arduino Serial Monitor and rerun.", ""])
    for state in sensors.values():
        age = time.time() - state.last_update if state.last_update else -1
        lines.append(f"{state.label} {state.address}")
        lines.append(f"  parsed: {state.parsed_count}  age: {age:0.2f}s")
        lines.append(f"  angle: {state.angle_deg[0]:7.2f} {state.angle_deg[1]:7.2f} {state.angle_deg[2]:7.2f}")
        lines.append(f"  acc:   {state.acc[0]:7.3f} {state.acc[1]:7.3f} {state.acc[2]:7.3f}")
        lines.append(f"  gyro:  {state.gyro[0]:7.1f} {state.gyro[1]:7.1f} {state.gyro[2]:7.1f}")
        lines.append("")
    lines.append("Recent serial lines:")
    lines.extend(list(raw_lines)[-18:])
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=8)


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize two WitMotion IMUs from Arduino serial output.")
    parser.add_argument("--port", help="Serial port, for example COM6.")
    parser.add_argument("--baud", type=int, help="Serial baudrate. Defaults to config value or 9600.")
    parser.add_argument("--config", type=Path, help="Calibration JSON path.")
    parser.add_argument("--list-ports", action="store_true", help="List serial ports and exit.")
    args = parser.parse_args()

    if args.list_ports:
        list_serial_ports()
        return 0

    config = load_config(args.config)
    serial_cfg = config.get("serial", {})
    port = args.port or serial_cfg.get("port") or "COM6"
    baudrate = args.baud or int(serial_cfg.get("baudrate", 9600))

    sensors = build_sensor_states(config)
    raw_lines: Deque[str] = deque(maxlen=80)
    data_queue: "queue.Queue[SerialEvent]" = queue.Queue()
    stop_event = threading.Event()
    reader = threading.Thread(target=serial_reader, args=(port, baudrate, data_queue, stop_event), daemon=True)
    reader.start()

    fig = plt.figure(figsize=(14, 7))
    try:
        fig.canvas.manager.set_window_title("Two IMU Realtime View")
    except AttributeError:
        pass

    serial_error: Optional[str] = None

    def animate(_frame):
        nonlocal serial_error
        latest_error = update_states(data_queue, sensors, raw_lines)
        if latest_error:
            serial_error = latest_error

        fig.clear()
        grid = GridSpec(2, 3, figure=fig, width_ratios=[1.35, 1.1, 1.15], height_ratios=[1, 1])
        ax3d = fig.add_subplot(grid[:, 0], projection="3d")
        ax_plot = fig.add_subplot(grid[:, 1])
        ax_text = fig.add_subplot(grid[:, 2])

        ax3d.set_title("Realtime Orientation + Tip Trace")
        ax3d.set_xlim(-2.7, 2.7)
        ax3d.set_ylim(-2.2, 2.2)
        ax3d.set_zlim(-1.7, 1.7)
        ax3d.set_xlabel("X")
        ax3d.set_ylabel("Y")
        ax3d.set_zlabel("Z")
        ax3d.view_init(elev=24, azim=-58)
        ax3d.set_box_aspect((5.4, 4.4, 3.4))
        draw_sensor(ax3d, sensors["sensor1"], np.array([-1.2, 0.0, 0.0]), COLORS["sensor1"])
        draw_sensor(ax3d, sensors["sensor2"], np.array([1.2, 0.0, 0.0]), COLORS["sensor2"])

        draw_angle_history(ax_plot, sensors)
        draw_data_panel(ax_text, sensors, raw_lines, port, baudrate, serial_error)
        fig.tight_layout()

    animation = FuncAnimation(fig, animate, interval=80, cache_frame_data=False)
    try:
        plt.show()
    finally:
        stop_event.set()
        reader.join(timeout=1.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

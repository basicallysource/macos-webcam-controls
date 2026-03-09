import argparse
import os
import select
import shutil
import sys
import termios
import time
import tty

from camera_preview import PreviewWindow, find_cv2_indices
from uvc_camera import UvcCameraController, UvcControllerError, formatCamera, listCameras, unrefCamera

PROFILE_LOG = "profile.log"


class Profiler:
    def __init__(self):
        self._timers = {}
        self._stats = {}
        self._loop_start = None
        self._loop_count = 0
        self._log_file = open(PROFILE_LOG, "w")

    def close(self):
        self._writeSummary()
        self._log_file.close()

    def loopStart(self):
        self._loop_start = time.perf_counter()
        self._loop_count += 1

    def loopEnd(self):
        if self._loop_start is not None:
            elapsed = time.perf_counter() - self._loop_start
            self._record("loop_total", elapsed)
            if elapsed > 0.1:
                self._log(f"SLOW loop #{self._loop_count}: {elapsed*1000:.1f}ms")

    def start(self, name):
        self._timers[name] = time.perf_counter()

    def stop(self, name):
        if name in self._timers:
            elapsed = time.perf_counter() - self._timers.pop(name)
            self._record(name, elapsed)

    def _record(self, name, elapsed):
        if name not in self._stats:
            self._stats[name] = {"count": 0, "total": 0.0, "max": 0.0}
        s = self._stats[name]
        s["count"] += 1
        s["total"] += elapsed
        s["max"] = max(s["max"], elapsed)

    def _log(self, msg):
        self._log_file.write(f"[{time.perf_counter():.3f}] {msg}\n")
        self._log_file.flush()

    def _writeSummary(self):
        self._log_file.write("\n=== PROFILE SUMMARY ===\n")
        self._log_file.write(f"{'name':<30} {'calls':>8} {'total':>10} {'avg':>10} {'max':>10}\n")
        for name, s in sorted(self._stats.items()):
            avg = s["total"] / s["count"] if s["count"] else 0
            self._log_file.write(
                f"{name:<30} {s['count']:>8} {s['total']*1000:>9.1f}ms {avg*1000:>9.2f}ms {s['max']*1000:>9.2f}ms\n"
            )
        self._log_file.write(f"\ntotal loops: {self._loop_count}\n")


def parseArgs():
    parser = argparse.ArgumentParser(description="Keyboard control for UVC webcam controls")
    parser.add_argument("camera_index", type=int, nargs="?", help="camera index from --list")
    parser.add_argument("--list", action="store_true", help="list discovered UVC webcams")
    return parser.parse_args()


def listOnlyAndExit(cameras):
    if not cameras:
        print("No UVC webcams found")
        return 1
    for index, cam in enumerate(cameras):
        print(formatCamera(cam, index))
    return 0


def clearScreen():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def terminalRows():
    return shutil.get_terminal_size((120, 40)).lines


def baseStep(info):
    if info.kind == "pair":
        if isinstance(info.resolution, tuple):
            return (info.resolution[0] if info.resolution[0] > 0 else 1, info.resolution[1] if info.resolution[1] > 0 else 1)
        return (1, 1)
    if isinstance(info.resolution, int) and info.resolution > 0:
        return info.resolution
    return 1


def currentStep(step_scale, info):
    if info.kind == "pair":
        pair_base = baseStep(info)
        return (max(1, pair_base[0] * step_scale), max(1, pair_base[1] * step_scale))
    return max(1, baseStep(info) * step_scale)


def boolLabel(value):
    return "on" if value else "off"


def enumLabel(spec, value):
    for enum_value, label in spec.get("enum_values", []):
        if enum_value == value:
            return label
    return str(value)


def formatValue(spec, info, value, active_axis):
    if info.kind == "bool":
        return boolLabel(bool(value))
    if info.kind == "enum":
        return enumLabel(spec, value)
    if info.kind == "pair":
        axis_markers = ["x", "y"]
        axis_markers[active_axis] = axis_markers[active_axis].upper()
        return f"{value[0]},{value[1]} ({axis_markers[0]}/{axis_markers[1]})"
    return str(value)


def formatRange(info):
    if info.kind == "pair":
        return f"{info.minimum[0]}..{info.maximum[0]} | {info.minimum[1]}..{info.maximum[1]}"
    if info.kind in ("bool", "enum"):
        return "-"
    return f"{info.minimum}..{info.maximum}"


def formatStep(info, step_size):
    if info.kind == "pair":
        return f"{step_size[0]},{step_size[1]}"
    if info.kind in ("bool", "enum"):
        return "toggle"
    return str(step_size)


def renderCameraPicker(cameras, selected_idx):
    clearScreen()
    print("Select Camera")
    print("keys: up/down (or k/j, w/s) to select, enter to open, q to quit")
    print("")
    for idx, camera in enumerate(cameras):
        prefix = ">" if idx == selected_idx else " "
        print(f"{prefix} {formatCamera(camera, idx)}")
    sys.stdout.flush()


def visibleWindow(selected_idx, total_items, max_visible):
    if total_items <= max_visible:
        return 0, total_items

    half = max_visible // 2
    start = max(0, selected_idx - half)
    end = start + max_visible
    if end > total_items:
        end = total_items
        start = end - max_visible
    return start, end


def renderControls(controller, control_ids, selected_idx, step_scales, pair_axis_map, value_input, preview_status, status_line):
    control_infos = []
    for control_id in control_ids:
        spec = controller.getControlSpec(control_id)
        info = controller.getControlInfo(control_id)
        value = controller.getControl(control_id)
        control_infos.append((control_id, spec, info, value))

    clearScreen()
    print(f"UVC keyboard control — {controller.camera_descriptor.display_name}")
    print("keys: up/down (or k/j, w/s) select, left/right adjust")
    print("keys: [ / ] step down/up, a axis for pan/tilt, v type value, c capture, r refresh, b cameras, q quit")
    if preview_status:
        print(f"preview: {preview_status}")
    if status_line:
        print(f"status: {status_line}")
    print("")

    rows = terminalRows()
    max_visible = max(4, rows - 12)
    start, end = visibleWindow(selected_idx, len(control_infos), max_visible)

    for idx in range(start, end):
        control_id, spec, info, value = control_infos[idx]
        selected = idx == selected_idx
        prefix = ">" if selected else " "
        step_size = currentStep(step_scales[control_id], info)
        value_text = formatValue(spec, info, value, pair_axis_map[control_id])
        range_text = formatRange(info)
        step_text = formatStep(info, step_size)
        print(f"{prefix} {spec['display']:<20} value={value_text:<18} range={range_text:<24} step={step_text}")

    if start > 0 or end < len(control_infos):
        print(f"\nshowing {start + 1}-{end} of {len(control_infos)}")

    if value_input is not None:
        _, spec, _, _ = control_infos[selected_idx]
        print("")
        print(f"type value for {spec['display']}: {value_input}")
        print("enter apply | esc cancel | backspace edit")

    sys.stdout.flush()


class CbreakKeyboard:
    def __enter__(self):
        self._fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._buffer = ""
        return self

    def __exit__(self, exc_type, exc, traceback):
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def readEvent(self, timeout_seconds):
        if not self._buffer:
            ready, _, _ = select.select([self._fd], [], [], timeout_seconds)
            if not ready:
                return None
            chunk = os.read(self._fd, 64)
            if not chunk:
                return None
            self._buffer += chunk.decode("latin-1", errors="ignore")
        else:
            ready, _, _ = select.select([self._fd], [], [], 0)
            if ready:
                chunk = os.read(self._fd, 64)
                if chunk:
                    self._buffer += chunk.decode("latin-1", errors="ignore")

        return self._popEvent()

    def _popEvent(self):
        if not self._buffer:
            return None

        first_char = self._buffer[0]
        if first_char != "\x1b":
            self._buffer = self._buffer[1:]
            if first_char in ("\r", "\n"):
                return "enter"
            if first_char in ("\x7f", "\x08"):
                return "backspace"
            return first_char

        if len(self._buffer) == 1:
            return None

        second_char = self._buffer[1]
        if second_char not in ("[", "O"):
            self._buffer = self._buffer[1:]
            return "esc"

        idx = 2
        while idx < len(self._buffer):
            cur = self._buffer[idx]
            if cur.isalpha() or cur == "~":
                sequence = self._buffer[: idx + 1]
                self._buffer = self._buffer[idx + 1 :]
                last = sequence[-1]
                if last == "A":
                    return "up"
                if last == "B":
                    return "down"
                if last == "C":
                    return "right"
                if last == "D":
                    return "left"
                return "esc"
            idx += 1

        ready, _, _ = select.select([self._fd], [], [], 0)
        if ready:
            chunk = os.read(self._fd, 64)
            if chunk:
                self._buffer += chunk.decode("latin-1", errors="ignore")
                return self._popEvent()
        return None


def clampWithInfo(target_value, info):
    if info.kind == "pair":
        values = []
        for idx in (0, 1):
            step = baseStep(info)[idx]
            clamped = min(max(target_value[idx], info.minimum[idx]), info.maximum[idx])
            clamped = info.minimum[idx] + ((clamped - info.minimum[idx]) // step) * step
            values.append(clamped)
        return (values[0], values[1])

    clamped = min(max(target_value, info.minimum), info.maximum)
    step = baseStep(info)
    return info.minimum + ((clamped - info.minimum) // step) * step


def adjustControl(controller, control_id, direction, step_scale, axis):
    spec = controller.getControlSpec(control_id)
    info = controller.getControlInfo(control_id)
    current = controller.getControl(control_id)

    if info.kind == "bool":
        return controller.setControl(control_id, not bool(current))

    if info.kind == "enum":
        values = [item[0] for item in spec.get("enum_values", [])]
        if not values:
            return current
        try:
            idx = values.index(current)
        except ValueError:
            idx = 0
        idx = (idx + direction) % len(values)
        return controller.setControl(control_id, values[idx])

    if info.kind == "pair":
        step_pair = currentStep(step_scale, info)
        updated = [current[0], current[1]]
        updated[axis] += direction * step_pair[axis]
        target = clampWithInfo((updated[0], updated[1]), info)
        return controller.setControl(control_id, target)

    step = currentStep(step_scale, info)
    target = clampWithInfo(current + direction * step, info)
    return controller.setControl(control_id, target)


def parseTypedValue(raw_value, spec, info):
    text = raw_value.strip().lower()
    if text == "":
        raise UvcControllerError("empty value")

    if info.kind == "bool":
        if text in ("1", "true", "on", "yes"):
            return True
        if text in ("0", "false", "off", "no"):
            return False
        raise UvcControllerError("bool value must be on/off or 1/0")

    if info.kind == "enum":
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        return text

    if info.kind == "pair":
        parts = [part.strip() for part in raw_value.split(",")]
        if len(parts) != 2:
            raise UvcControllerError("pair value must look like x,y")
        first = int(parts[0])
        second = int(parts[1])
        return (first, second)

    return int(raw_value)


def pickCamera(cameras):
    if not cameras:
        return None

    selected_idx = 0
    with CbreakKeyboard() as keyboard:
        renderCameraPicker(cameras, selected_idx)
        while True:
            event = keyboard.readEvent(0.05)
            if event is None:
                continue
            if event == "q":
                return None
            if event in ("up", "k", "w"):
                selected_idx = (selected_idx - 1) % len(cameras)
                renderCameraPicker(cameras, selected_idx)
            elif event in ("down", "j", "s"):
                selected_idx = (selected_idx + 1) % len(cameras)
                renderCameraPicker(cameras, selected_idx)
            elif event == "enter":
                return selected_idx


def runLoop(controller, cv2_index):
    controller.forceManualMode()

    control_ids = controller.getSupportedControlIds()
    if not control_ids:
        raise UvcControllerError("no supported controls on this camera")

    step_scales = {control_id: 1 for control_id in control_ids}
    pair_axis_map = {control_id: 0 for control_id in control_ids}
    selected_idx = 0
    value_input = None
    status_line = ""

    preview = PreviewWindow(controller.camera_descriptor)
    preview.start(cv2_index)
    profiler = Profiler()

    try:
        with CbreakKeyboard() as keyboard:
            renderControls(controller, control_ids, selected_idx, step_scales, pair_axis_map, value_input, preview.status, status_line)

            while True:
                profiler.loopStart()

                profiler.start("preview.update")
                preview.update()
                profiler.stop("preview.update")

                profiler.start("keyboard.readEvent")
                event = keyboard.readEvent(0.02)
                profiler.stop("keyboard.readEvent")

                if event is None:
                    profiler.loopEnd()
                    continue

                profiler.start("getControlInfo")
                control_id = control_ids[selected_idx]
                info = controller.getControlInfo(control_id)
                profiler.stop("getControlInfo")
                status_line = ""

                if value_input is not None:
                    if event == "esc":
                        value_input = None
                    elif event == "enter":
                        try:
                            spec = controller.getControlSpec(control_id)
                            parsed = parseTypedValue(value_input, spec, info)
                            controller.setControl(control_id, parsed)
                            status_line = "value applied"
                        except Exception as exc:
                            status_line = f"apply failed: {exc}"
                        value_input = None
                    elif event == "backspace":
                        value_input = value_input[:-1]
                    elif isinstance(event, str) and len(event) == 1 and event in "0123456789,-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        value_input += event

                    profiler.start("renderControls")
                    renderControls(controller, control_ids, selected_idx, step_scales, pair_axis_map, value_input, preview.status, status_line)
                    profiler.stop("renderControls")
                    profiler.loopEnd()
                    continue

                if event == "q":
                    return "quit"
                if event == "b":
                    return "back"
                if event in ("up", "k", "w"):
                    selected_idx = (selected_idx - 1) % len(control_ids)
                elif event in ("down", "j", "s"):
                    selected_idx = (selected_idx + 1) % len(control_ids)
                elif event == "left":
                    try:
                        adjustControl(controller, control_id, -1, step_scales[control_id], pair_axis_map[control_id])
                    except Exception as exc:
                        status_line = f"adjust failed: {exc}"
                elif event == "right":
                    try:
                        adjustControl(controller, control_id, 1, step_scales[control_id], pair_axis_map[control_id])
                    except Exception as exc:
                        status_line = f"adjust failed: {exc}"
                elif event == "[":
                    step_scales[control_id] = max(1, step_scales[control_id] // 2)
                elif event == "]":
                    step_scales[control_id] = min(4096, step_scales[control_id] * 2)
                elif event == "a":
                    if info.kind == "pair":
                        pair_axis_map[control_id] = 1 - pair_axis_map[control_id]
                elif event == "c":
                    status_line = preview.saveCapture()
                elif event == "v":
                    value_input = ""
                elif event == "r":
                    pass
                else:
                    continue

                profiler.start("renderControls")
                renderControls(controller, control_ids, selected_idx, step_scales, pair_axis_map, value_input, preview.status, status_line)
                profiler.stop("renderControls")

                profiler.loopEnd()
    finally:
        profiler.close()
        preview.stop()

    return "quit"


def probeCv2Mapping(cameras):
    """Probe all cameras at once to find their cv2 indices. See camera_preview.py."""
    controllers = []
    try:
        for cam in cameras:
            ctrl = UvcCameraController(cam)
            ctrl.open()
            controllers.append((cam, ctrl))
        print("detecting preview cameras...")
        mapping = find_cv2_indices(controllers)
    finally:
        for _, ctrl in controllers:
            ctrl.close()
    # Convert from id(descriptor) -> cv2_index to list_index -> cv2_index
    return {i: mapping[id(cam)] for i, cam in enumerate(cameras) if id(cam) in mapping}


def main():
    args = parseArgs()
    cameras = listCameras()

    try:
        if args.list:
            return listOnlyAndExit(cameras)

        if not cameras:
            print("No UVC webcams found")
            return 1

        cv2_mapping = probeCv2Mapping(cameras)

        selected_camera_index = args.camera_index
        while True:
            if selected_camera_index is None:
                selected_camera_index = pickCamera(cameras)
                if selected_camera_index is None:
                    return 0

            if selected_camera_index < 0 or selected_camera_index >= len(cameras):
                print(f"invalid camera_index={selected_camera_index}")
                return 1

            camera = cameras[selected_camera_index]
            print(f"selected {formatCamera(camera, selected_camera_index)}")

            cv2_index = cv2_mapping.get(selected_camera_index)
            with UvcCameraController(camera) as controller:
                result = runLoop(controller, cv2_index)

            if result == "back":
                selected_camera_index = None
                continue
            return 0
    except (UvcControllerError, KeyboardInterrupt) as exc:
        print(f"error: {exc}")
        return 1
    finally:
        for camera in cameras:
            unrefCamera(camera)


if __name__ == "__main__":
    raise SystemExit(main())

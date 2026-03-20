"""
Shared TUI utilities: keyboard input, camera picker, screen helpers.
Used by camera_keyboard_ui.py and capture_range.py.
"""

import os
import select
import sys
import termios
import tty

from camera_preview import find_cv2_indices
from uvc_camera import UvcCameraController, formatCamera


def clearScreen():
    sys.stdout.write("\x1b[2J\x1b[H")
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

        self._buffer = self._buffer[1:]
        return "esc"


def renderCameraPicker(cameras, selected_idx):
    clearScreen()
    print("Select Camera")
    print("keys: up/down (or k/j, w/s) to select, enter to open, q to quit")
    print("")
    for idx, camera in enumerate(cameras):
        prefix = ">" if idx == selected_idx else " "
        print(f"{prefix} {formatCamera(camera, idx)}")
    sys.stdout.flush()


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
    return {i: mapping[id(cam)] for i, cam in enumerate(cameras) if id(cam) in mapping}

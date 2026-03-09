"""
Camera preview via OpenCV with automatic cv2 index discovery.

Problem: This app controls UVC cameras via libusb, but shows a live preview
via OpenCV (cv2). These two systems enumerate cameras independently:
- libusb discovers USB devices by walking the USB bus
- cv2 uses macOS AVFoundation, which has its own ordering

There is no API to ask "which cv2 index corresponds to this USB device."
The orderings do not match and are not predictable.

Solution: At startup we discover the correct cv2 index for each camera by
using UVC brightness as a side channel. For each UVC camera, we iterate
through cv2 indices, opening one capture at a time (to avoid USB bandwidth
exhaustion), temporarily set brightness to minimum via libusb, and check if
the cv2 feed gets darker. A large brightness drop means that cv2 index is
showing our camera.

We test each cv2 index one at a time rather than opening all captures at
once because multiple USB cameras sharing a bus cannot stream simultaneously.

This runs once at startup and takes a few seconds per camera, but gives a
verified mapping. If brightness probing fails (camera doesn't support
brightness, or cv2/numpy is not installed), the preview is simply disabled
-- it never shows the wrong camera.
"""

import os
import subprocess
import time
from datetime import datetime

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

PREVIEW_WINDOW_NAME = "Camera Preview"

# Minimum brightness drop (0-255 scale) to consider a cv2 index as matching.
_BRIGHTNESS_DROP_THRESHOLD = 5.0


def _get_skip_indices():
    """
    If IGNORE_WIRELESS_IPHONE=1 is set, find the cv2 index of any iPhone
    Continuity Camera and return it so the brightness probe skips it.
    Saves a few seconds of probing per camera since the iPhone is never
    a UVC device but still occupies a cv2/AVFoundation index.
    """
    if os.environ.get("IGNORE_WIRELESS_IPHONE") != "1":
        return set()
    try:
        swift_code = (
            "import AVFoundation\n"
            "let d = AVCaptureDevice.devices(for: .video)\n"
            "for (i, dev) in d.enumerated() {\n"
            "    if dev.localizedName.contains(\"iPhone\") || dev.modelID.contains(\"iPhone\") { print(i) }\n"
            "}\n"
        )
        result = subprocess.run(
            ["swift", "-"], input=swift_code,
            capture_output=True, text=True, timeout=15,
        )
        return {int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()}
    except Exception:
        return set()


def find_cv2_indices(controllers):
    """
    Find which cv2 camera index corresponds to each UVC camera.

    For each UVC camera, opens cv2 captures one at a time and toggles
    brightness to identify the match. Sequential capture avoids USB
    bandwidth issues that prevent multiple cameras from streaming at once.

    Args:
        controllers: list of (camera_descriptor, open UvcCameraController) pairs

    Returns:
        dict mapping id(camera_descriptor) -> cv2 index
    """
    if cv2 is None or np is None:
        return {}

    # Find which cv2 indices to skip (e.g. iPhone Continuity Camera)
    skip_indices = _get_skip_indices()

    # Discover how many cv2 indices exist
    available_indices = []
    for idx in range(10):
        if idx in skip_indices:
            continue
        cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            available_indices.append(idx)
        cap.release()

    if not available_indices:
        return {}

    results = {}  # id(camera_descriptor) -> cv2 index
    claimed_indices = set()

    for camera_descriptor, controller in controllers:
        # Check if this camera supports brightness control
        try:
            info = controller.getControlInfo("brightness")
            if not info.is_capable:
                continue
            original_brightness = controller.getControl("brightness")
            min_brightness = info.minimum
        except Exception:
            continue

        match = _probe_single_camera(
            controller, original_brightness, min_brightness,
            available_indices, claimed_indices,
        )
        if match is not None:
            results[id(camera_descriptor)] = match
            claimed_indices.add(match)

    return results


def _probe_single_camera(controller, original_brightness, min_brightness,
                         available_indices, claimed_indices):
    """
    Probe each cv2 index one at a time to find which one matches this camera.
    Opens and closes captures sequentially to avoid USB bandwidth issues.
    """
    best_idx = None
    best_drop = 0.0

    for idx in available_indices:
        if idx in claimed_indices:
            continue

        cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
        if not cap.isOpened():
            cap.release()
            continue

        # Read baseline
        baseline = _grab_mean_brightness(cap)
        if baseline is None:
            cap.release()
            continue

        # Dim via UVC
        try:
            controller.setControl("brightness", min_brightness)
        except Exception:
            cap.release()
            continue

        time.sleep(0.4)

        # Read dimmed
        dimmed = _grab_mean_brightness(cap)

        # Restore
        try:
            controller.setControl("brightness", original_brightness)
        except Exception:
            pass

        cap.release()
        time.sleep(0.2)

        if dimmed is None:
            continue

        drop = baseline - dimmed
        if drop > best_drop:
            best_drop = drop
            best_idx = idx

    if best_idx is not None and best_drop > _BRIGHTNESS_DROP_THRESHOLD:
        return best_idx
    return None


def _grab_mean_brightness(cap, num_frames=5):
    """Read a few frames and return the average pixel brightness of the last one."""
    frame = None
    for _ in range(num_frames):
        ok, f = cap.read()
        if ok:
            frame = f
    if frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


class PreviewWindow:
    """
    Live camera preview window. Uses brightness probing to discover the
    correct cv2 capture index, then shows the feed in an OpenCV window.
    """

    def __init__(self, camera_descriptor):
        self._camera_descriptor = camera_descriptor
        self._capture = None
        self._status = "off"
        self._failed = False
        self._last_frame = None

    @property
    def status(self):
        return self._status

    def start(self, cv2_index):
        """Start the preview with a known cv2 index (from find_cv2_indices)."""
        if cv2 is None:
            self._status = "opencv not installed"
            return

        if cv2_index is None:
            self._status = "camera not detected"
            return

        capture = cv2.VideoCapture(cv2_index, cv2.CAP_AVFOUNDATION)
        if not capture.isOpened():
            capture.release()
            self._status = "failed to open"
            return

        self._capture = capture
        self._status = f"running (cv2[{cv2_index}])"

    def stop(self):
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._last_frame = None
        if cv2 is not None:
            try:
                cv2.destroyWindow(PREVIEW_WINDOW_NAME)
                cv2.waitKey(1)
            except cv2.error:
                pass

    def update(self):
        if self._capture is None or cv2 is None or self._failed:
            return
        try:
            ok, frame = self._capture.read()
            if ok:
                self._last_frame = frame
                cv2.imshow(PREVIEW_WINDOW_NAME, frame)
            cv2.waitKey(1)
        except cv2.error:
            self._failed = True
            self._status = "opencv display failed"

    def saveCapture(self):
        if cv2 is None:
            return "opencv not installed"
        if self._last_frame is None:
            return "no frame available"
        captures_dir = os.path.join(os.getcwd(), "captures")
        os.makedirs(captures_dir, exist_ok=True)
        name = self._camera_descriptor.display_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.jpg"
        path = os.path.join(captures_dir, filename)
        cv2.imwrite(path, self._last_frame)
        return f"saved {filename}"

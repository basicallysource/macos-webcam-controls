# Actual macOS Webcam Controls in Python

Everything based on AVFoundation seems to be completely fake. [This great app](https://github.com/itaybre/CameraController/) is the only thing that seems to work programmatically for controlling exposure, white balance, etc. on a USB webcam on macOS. This repo is merely a translation of that work into Python.

## Run The UI

From the repository root:

```bash
uv run python camera_keyboard_ui.py
```

Optional:

```bash
uv run python camera_keyboard_ui.py --list
uv run python camera_keyboard_ui.py 1
```

## Apply Settings From JSON

Use `set.py` to apply settings without opening the UI.

```bash
uv run python set.py config.json --dry-run
uv run python set.py config.json
uv run python set.py config.json --verbose --force-manual
```

You can copy `example_config.json` as a starting point:

```bash
cp example_config.json config.json
```

Config structure:

- `cameras`: list of rules
- each rule has:
  - matcher fields (any combination): `index`, `name`, `name_contains`, `bus`, `addr`, `vid`, `pid`
  - `settings`: object of control IDs to values

## `uvc_camera.py` API

### Top-level functions

- `listCameras() -> list[UvcCameraDescriptor]`
  - Discover available UVC cameras.
- `unrefCamera(camera_descriptor) -> None`
  - Release a camera descriptor from `listCameras`.
- `formatCamera(camera_descriptor, index) -> str`
  - Build a display string for a camera.

### `UvcCameraDescriptor`

Fields:

- `vendor_id`, `product_id`
- `bus_number`, `device_address`
- `interface_number`
- `processing_unit_id`, `camera_terminal_id`
- `product_name`, `manufacturer_name`, `display_name`

### `UvcCameraController`

Use as a context manager:

```python
from uvc_camera import listCameras, UvcCameraController, unrefCamera

cameras = listCameras()
try:
    with UvcCameraController(cameras[0]) as controller:
        ids = controller.getSupportedControlIds()
        value = controller.getControl("exposure_time")
        controller.setControl("exposure_time", value + 1)
finally:
    for cam in cameras:
        unrefCamera(cam)
```

Methods:

- `open()` / `close()`
- `getSupportedControlIds() -> list[str]`
- `getControlSpec(control_id) -> dict`
- `getControlInfo(control_id) -> UvcControlInfo`
- `getControl(control_id) -> int | bool | tuple[int, int]`
- `setControl(control_id, value) -> value`
- `forceManualMode() -> None`
  - Forces only exposure mode to manual.

### `UvcControlInfo`

Fields:

- `is_capable`
- `kind` (`int`, `bool`, `enum`, `pair`)
- `current`
- `minimum`, `maximum`, `resolution`

### Control IDs

The module supports these IDs (only capable controls are exposed by `getSupportedControlIds()`):

- `scanning_mode`
- `exposure_mode`, `exposure_priority`, `exposure_time`
- `gain`
- `brightness`, `contrast`, `contrast_auto`
- `saturation`, `sharpness`
- `hue`, `hue_auto`
- `gamma`
- `white_balance`, `white_balance_auto`
- `white_balance_component`, `white_balance_component_auto`
- `power_line_frequency`
- `backlight_compensation`
- `focus_auto`, `focus_absolute`
- `iris_absolute`
- `zoom_absolute`
- `pan_tilt_absolute`
- `roll_absolute`

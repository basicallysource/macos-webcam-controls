import atexit
import ctypes
from ctypes import POINTER, byref, c_int, c_uint8, c_uint16, c_uint32, c_void_p, cast

LIBUSB_PATH = "/opt/homebrew/lib/libusb-1.0.dylib"
LIBUSB_ENDPOINT_IN = 0x80
LIBUSB_ENDPOINT_OUT = 0x00
LIBUSB_REQUEST_TYPE_CLASS = 0x20
LIBUSB_RECIPIENT_INTERFACE = 0x01
LIBUSB_BMREQ_IN = LIBUSB_ENDPOINT_IN | LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE
LIBUSB_BMREQ_OUT = LIBUSB_ENDPOINT_OUT | LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE
LIBUSB_SUCCESS = 0
LIBUSB_ERROR_ACCESS = -3
LIBUSB_ERROR_BUSY = -6
LIBUSB_CLASS_VIDEO = 0x0E
LIBUSB_SUBCLASS_VIDEO_CONTROL = 0x01
CS_INTERFACE_DESCRIPTOR_TYPE = 0x24
UVC_SUBTYPE_INPUT_TERMINAL = 0x02
UVC_SUBTYPE_PROCESSING_UNIT = 0x05
CAMERA_TERMINAL_TYPE = 0x0201

UVC_SET_CUR = 0x01
UVC_GET_CUR = 0x81
UVC_GET_MIN = 0x82
UVC_GET_MAX = 0x83
UVC_GET_RES = 0x84
UVC_GET_INFO = 0x86

CT_SCANNING_MODE = 0x01
CT_AE_MODE = 0x02
CT_AE_PRIORITY = 0x03
CT_EXPOSURE_TIME_ABSOLUTE = 0x04
CT_FOCUS_ABSOLUTE = 0x06
CT_FOCUS_AUTO = 0x08
CT_IRIS_ABSOLUTE = 0x09
CT_ZOOM_ABSOLUTE = 0x0B
CT_PAN_TILT_ABSOLUTE = 0x0D
CT_ROLL_ABSOLUTE = 0x0F

PU_BACKLIGHT_COMPENSATION = 0x01
PU_BRIGHTNESS = 0x02
PU_CONTRAST = 0x03
PU_GAIN = 0x04
PU_POWER_LINE_FREQUENCY = 0x05
PU_HUE = 0x06
PU_SATURATION = 0x07
PU_SHARPNESS = 0x08
PU_GAMMA = 0x09
PU_WHITE_BALANCE_TEMPERATURE = 0x0A
PU_WHITE_BALANCE_TEMPERATURE_AUTO = 0x0B
PU_WHITE_BALANCE_COMPONENT = 0x0C
PU_WHITE_BALANCE_COMPONENT_AUTO = 0x0D
PU_HUE_AUTO = 0x10
PU_CONTRAST_AUTO = 0x13

AE_MODE_MANUAL = 0x01
AE_MODE_AUTO = 0x02
AE_MODE_SHUTTER_PRIORITY = 0x04
AE_MODE_APERTURE_PRIORITY = 0x08
WB_AUTO_OFF = 0
PANTILT_SCALE = 3600

CONTROL_ORDER = [
    "scanning_mode",
    "exposure_mode",
    "exposure_priority",
    "exposure_time",
    "gain",
    "brightness",
    "contrast",
    "contrast_auto",
    "saturation",
    "sharpness",
    "hue",
    "hue_auto",
    "gamma",
    "white_balance",
    "white_balance_auto",
    "white_balance_component",
    "white_balance_component_auto",
    "power_line_frequency",
    "backlight_compensation",
    "focus_auto",
    "focus_absolute",
    "iris_absolute",
    "zoom_absolute",
    "pan_tilt_absolute",
    "roll_absolute",
]

CONTROL_SPECS = {
    "scanning_mode": {
        "display": "Scanning Mode",
        "kind": "bool",
        "selector": CT_SCANNING_MODE,
        "size": 1,
        "unit_key": "camera_terminal_id",
    },
    "exposure_mode": {
        "display": "Exposure Mode",
        "kind": "enum",
        "selector": CT_AE_MODE,
        "size": 1,
        "unit_key": "camera_terminal_id",
        "enum_values": [
            (AE_MODE_MANUAL, "manual"),
            (AE_MODE_AUTO, "auto"),
            (AE_MODE_SHUTTER_PRIORITY, "shutter_priority"),
            (AE_MODE_APERTURE_PRIORITY, "aperture_priority"),
        ],
    },
    "exposure_priority": {
        "display": "Exposure Priority",
        "kind": "int",
        "selector": CT_AE_PRIORITY,
        "size": 1,
        "unit_key": "camera_terminal_id",
        "clamp": True,
    },
    "exposure_time": {
        "display": "Exposure Time",
        "kind": "int",
        "selector": CT_EXPOSURE_TIME_ABSOLUTE,
        "size": 4,
        "unit_key": "camera_terminal_id",
        "clamp": True,
    },
    "focus_absolute": {
        "display": "Focus",
        "kind": "int",
        "selector": CT_FOCUS_ABSOLUTE,
        "size": 2,
        "unit_key": "camera_terminal_id",
        "clamp": True,
    },
    "focus_auto": {
        "display": "Focus Auto",
        "kind": "bool",
        "selector": CT_FOCUS_AUTO,
        "size": 1,
        "unit_key": "camera_terminal_id",
    },
    "iris_absolute": {
        "display": "Iris",
        "kind": "int",
        "selector": CT_IRIS_ABSOLUTE,
        "size": 2,
        "unit_key": "camera_terminal_id",
        "clamp": True,
    },
    "zoom_absolute": {
        "display": "Zoom",
        "kind": "int",
        "selector": CT_ZOOM_ABSOLUTE,
        "size": 2,
        "unit_key": "camera_terminal_id",
        "clamp": True,
    },
    "pan_tilt_absolute": {
        "display": "Pan/Tilt",
        "kind": "pair",
        "selector": CT_PAN_TILT_ABSOLUTE,
        "size": 8,
        "unit_key": "camera_terminal_id",
        "signed": True,
        "scale": PANTILT_SCALE,
        "clamp": True,
    },
    "roll_absolute": {
        "display": "Roll",
        "kind": "int",
        "selector": CT_ROLL_ABSOLUTE,
        "size": 2,
        "unit_key": "camera_terminal_id",
        "signed": True,
        "clamp": True,
    },
    "backlight_compensation": {
        "display": "Backlight",
        "kind": "int",
        "selector": PU_BACKLIGHT_COMPENSATION,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "brightness": {
        "display": "Brightness",
        "kind": "int",
        "selector": PU_BRIGHTNESS,
        "size": 2,
        "unit_key": "processing_unit_id",
        "signed": True,
        "clamp": True,
    },
    "contrast": {
        "display": "Contrast",
        "kind": "int",
        "selector": PU_CONTRAST,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "contrast_auto": {
        "display": "Contrast Auto",
        "kind": "bool",
        "selector": PU_CONTRAST_AUTO,
        "size": 1,
        "unit_key": "processing_unit_id",
    },
    "gain": {
        "display": "Gain",
        "kind": "int",
        "selector": PU_GAIN,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "power_line_frequency": {
        "display": "Power Line",
        "kind": "int",
        "selector": PU_POWER_LINE_FREQUENCY,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "hue": {
        "display": "Hue",
        "kind": "int",
        "selector": PU_HUE,
        "size": 2,
        "unit_key": "processing_unit_id",
        "signed": True,
        "clamp": True,
    },
    "hue_auto": {
        "display": "Hue Auto",
        "kind": "bool",
        "selector": PU_HUE_AUTO,
        "size": 1,
        "unit_key": "processing_unit_id",
    },
    "saturation": {
        "display": "Saturation",
        "kind": "int",
        "selector": PU_SATURATION,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "sharpness": {
        "display": "Sharpness",
        "kind": "int",
        "selector": PU_SHARPNESS,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "gamma": {
        "display": "Gamma",
        "kind": "int",
        "selector": PU_GAMMA,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "white_balance": {
        "display": "White Balance",
        "kind": "int",
        "selector": PU_WHITE_BALANCE_TEMPERATURE,
        "size": 2,
        "unit_key": "processing_unit_id",
        "clamp": True,
    },
    "white_balance_auto": {
        "display": "White Balance Auto",
        "kind": "bool",
        "selector": PU_WHITE_BALANCE_TEMPERATURE_AUTO,
        "size": 1,
        "unit_key": "processing_unit_id",
    },
    "white_balance_component": {
        "display": "WB Component",
        "kind": "pair",
        "selector": PU_WHITE_BALANCE_COMPONENT,
        "size": 4,
        "unit_key": "processing_unit_id",
        "signed": False,
        "part_size": 2,
        "scale": 1,
        "clamp": True,
    },
    "white_balance_component_auto": {
        "display": "WB Component Auto",
        "kind": "bool",
        "selector": PU_WHITE_BALANCE_COMPONENT_AUTO,
        "size": 1,
        "unit_key": "processing_unit_id",
    },
}


class LibusbDeviceDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", c_uint8),
        ("bDescriptorType", c_uint8),
        ("bcdUSB", c_uint16),
        ("bDeviceClass", c_uint8),
        ("bDeviceSubClass", c_uint8),
        ("bDeviceProtocol", c_uint8),
        ("bMaxPacketSize0", c_uint8),
        ("idVendor", c_uint16),
        ("idProduct", c_uint16),
        ("bcdDevice", c_uint16),
        ("iManufacturer", c_uint8),
        ("iProduct", c_uint8),
        ("iSerialNumber", c_uint8),
        ("bNumConfigurations", c_uint8),
    ]


class LibusbEndpointDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", c_uint8),
        ("bDescriptorType", c_uint8),
        ("bEndpointAddress", c_uint8),
        ("bmAttributes", c_uint8),
        ("wMaxPacketSize", c_uint16),
        ("bInterval", c_uint8),
        ("bRefresh", c_uint8),
        ("bSynchAddress", c_uint8),
        ("extra", POINTER(c_uint8)),
        ("extra_length", c_int),
    ]


class LibusbInterfaceDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", c_uint8),
        ("bDescriptorType", c_uint8),
        ("bInterfaceNumber", c_uint8),
        ("bAlternateSetting", c_uint8),
        ("bNumEndpoints", c_uint8),
        ("bInterfaceClass", c_uint8),
        ("bInterfaceSubClass", c_uint8),
        ("bInterfaceProtocol", c_uint8),
        ("iInterface", c_uint8),
        ("endpoint", POINTER(LibusbEndpointDescriptor)),
        ("extra", POINTER(c_uint8)),
        ("extra_length", c_int),
    ]


class LibusbInterface(ctypes.Structure):
    _fields_ = [
        ("altsetting", POINTER(LibusbInterfaceDescriptor)),
        ("num_altsetting", c_int),
    ]


class LibusbConfigDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", c_uint8),
        ("bDescriptorType", c_uint8),
        ("wTotalLength", c_uint16),
        ("bNumInterfaces", c_uint8),
        ("bConfigurationValue", c_uint8),
        ("iConfiguration", c_uint8),
        ("bmAttributes", c_uint8),
        ("MaxPower", c_uint8),
        ("interface", POINTER(LibusbInterface)),
        ("extra", POINTER(c_uint8)),
        ("extra_length", c_int),
    ]


class UvcCameraDescriptor:
    def __init__(
        self,
        libusb_dev,
        vendor_id,
        product_id,
        bus_number,
        device_address,
        interface_number,
        processing_unit_id,
        camera_terminal_id,
        product_name,
        manufacturer_name,
    ):
        self.libusb_dev = libusb_dev
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.bus_number = bus_number
        self.device_address = device_address
        self.interface_number = interface_number
        self.processing_unit_id = processing_unit_id
        self.camera_terminal_id = camera_terminal_id
        self.product_name = product_name
        self.manufacturer_name = manufacturer_name

    @property
    def display_name(self):
        if self.product_name and self.manufacturer_name:
            return f"{self.manufacturer_name} {self.product_name}"
        if self.product_name:
            return self.product_name
        if self.manufacturer_name:
            return self.manufacturer_name
        return "Unknown Camera"


class UvcControlInfo:
    def __init__(self, minimum, maximum, resolution, current, is_capable, kind):
        self.minimum = minimum
        self.maximum = maximum
        self.resolution = resolution
        self.current = current
        self.is_capable = is_capable
        self.kind = kind


class UvcControllerError(Exception):
    pass


class UvcCameraController:
    def __init__(self, camera_descriptor):
        self.camera_descriptor = camera_descriptor
        self._lib = _getLibusb()
        self._handle = c_void_p()
        self._interface_claimed = False

    def open(self):
        result = self._lib.libusb_open(self.camera_descriptor.libusb_dev, byref(self._handle))
        if result != LIBUSB_SUCCESS:
            raise UvcControllerError(f"libusb_open failed: {result}")

        if self._lib.libusb_kernel_driver_active(self._handle, self.camera_descriptor.interface_number) == 1:
            self._lib.libusb_detach_kernel_driver(self._handle, self.camera_descriptor.interface_number)

        result = self._lib.libusb_claim_interface(self._handle, self.camera_descriptor.interface_number)
        if result == LIBUSB_SUCCESS:
            self._interface_claimed = True
            return
        if result in (LIBUSB_ERROR_ACCESS, LIBUSB_ERROR_BUSY):
            self._interface_claimed = False
            return

        self.close()
        raise UvcControllerError(f"libusb_claim_interface failed: {result}")

    def close(self):
        if self._handle:
            if self._interface_claimed:
                self._lib.libusb_release_interface(self._handle, self.camera_descriptor.interface_number)
                self._interface_claimed = False
            self._lib.libusb_close(self._handle)
            self._handle = c_void_p()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def getSupportedControlIds(self):
        control_ids = []
        for control_id in CONTROL_ORDER:
            info = self.getControlInfo(control_id)
            if info.is_capable:
                control_ids.append(control_id)
        return control_ids

    def getControlSpec(self, control_id):
        return _getControlSpec(control_id)

    def getControlInfo(self, control_id):
        control_spec = _getControlSpec(control_id)
        try:
            is_capable = self._getRaw(control_spec, UVC_GET_INFO, 1)[0] != 0
        except UvcControllerError:
            return UvcControlInfo(0, 0, 0, 0, False, control_spec["kind"])

        if not is_capable:
            return UvcControlInfo(0, 0, 0, 0, False, control_spec["kind"])

        current = self.getControl(control_id)

        if control_spec["kind"] in ("bool", "enum"):
            return UvcControlInfo(0, 0, 0, current, True, control_spec["kind"])

        minimum = _safeGetValue(self, control_spec, UVC_GET_MIN, current)
        maximum = _safeGetValue(self, control_spec, UVC_GET_MAX, current)
        resolution = _safeGetValue(self, control_spec, UVC_GET_RES, 1 if control_spec["kind"] == "int" else (1, 1))

        return UvcControlInfo(minimum, maximum, resolution, current, True, control_spec["kind"])

    def getControl(self, control_id):
        control_spec = _getControlSpec(control_id)
        raw = self._getRaw(control_spec, UVC_GET_CUR, control_spec["size"])
        return _decodeControlValue(control_spec, raw)

    def setControl(self, control_id, value):
        control_spec = _getControlSpec(control_id)

        if control_spec["kind"] == "int" and control_spec.get("clamp", False):
            value = _clampIntControl(self, control_id, int(value))
        elif control_spec["kind"] == "pair" and control_spec.get("clamp", False):
            value = _clampPairControl(self, control_id, value)
        elif control_spec["kind"] == "bool":
            value = bool(value)
        elif control_spec["kind"] == "enum":
            value = _normalizeEnumValue(control_spec, value)

        payload = _encodeControlValue(control_spec, value)
        self._setRaw(control_spec, payload)
        return value

    def forceManualMode(self):
        for control_id, value in (("exposure_mode", AE_MODE_MANUAL),):
            try:
                info = self.getControlInfo(control_id)
                if info.is_capable:
                    self.setControl(control_id, value)
            except UvcControllerError:
                pass

    def _getRaw(self, control_spec, request_code, size):
        buffer = (c_uint8 * size)()
        transferred = self._lib.libusb_control_transfer(
            self._handle,
            LIBUSB_BMREQ_IN,
            request_code,
            control_spec["selector"] << 8,
            _buildWIndex(self.camera_descriptor, control_spec),
            cast(buffer, POINTER(c_uint8)),
            size,
            1000,
        )
        if transferred < 0:
            raise UvcControllerError(f"control GET failed request=0x{request_code:02x} err={transferred}")
        return bytes(buffer[:size])

    def _setRaw(self, control_spec, payload):
        size = len(payload)
        buffer = (c_uint8 * size).from_buffer_copy(payload)
        transferred = self._lib.libusb_control_transfer(
            self._handle,
            LIBUSB_BMREQ_OUT,
            UVC_SET_CUR,
            control_spec["selector"] << 8,
            _buildWIndex(self.camera_descriptor, control_spec),
            cast(buffer, POINTER(c_uint8)),
            size,
            1000,
        )
        if transferred < 0:
            raise UvcControllerError(f"control SET failed selector=0x{control_spec['selector']:02x} err={transferred}")


def listCameras():
    lib = _getLibusb()
    context = _getLibusbContext()

    devices_ptr = POINTER(c_void_p)()
    count = lib.libusb_get_device_list(context, byref(devices_ptr))
    cameras = []
    seen_keys = set()

    try:
        if count < 0:
            raise UvcControllerError(f"libusb_get_device_list failed: {count}")

        for index in range(count):
            dev = devices_ptr[index]
            descriptor = LibusbDeviceDescriptor()
            if lib.libusb_get_device_descriptor(dev, byref(descriptor)) != LIBUSB_SUCCESS:
                continue

            config_desc_ptr = POINTER(LibusbConfigDescriptor)()
            if lib.libusb_get_active_config_descriptor(dev, byref(config_desc_ptr)) != LIBUSB_SUCCESS:
                continue

            try:
                config_desc = config_desc_ptr.contents
                uvc_details = _findUvcDetails(config_desc)
                if not uvc_details:
                    continue

                interface_number, processing_unit_id, camera_terminal_id = uvc_details
                bus_number = int(lib.libusb_get_bus_number(dev))
                device_address = int(lib.libusb_get_device_address(dev))
                dedupe_key = (bus_number, device_address, interface_number)
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                product_name = _readUsbString(lib, dev, int(descriptor.iProduct))
                manufacturer_name = _readUsbString(lib, dev, int(descriptor.iManufacturer))

                cameras.append(
                    UvcCameraDescriptor(
                        libusb_dev=dev,
                        vendor_id=int(descriptor.idVendor),
                        product_id=int(descriptor.idProduct),
                        bus_number=bus_number,
                        device_address=device_address,
                        interface_number=interface_number,
                        processing_unit_id=processing_unit_id,
                        camera_terminal_id=camera_terminal_id,
                        product_name=product_name,
                        manufacturer_name=manufacturer_name,
                    )
                )
                lib.libusb_ref_device(dev)
            finally:
                lib.libusb_free_config_descriptor(config_desc_ptr)
    finally:
        if bool(devices_ptr):
            lib.libusb_free_device_list(devices_ptr, 1)

    return cameras


def unrefCamera(camera_descriptor):
    _getLibusb().libusb_unref_device(camera_descriptor.libusb_dev)


def formatCamera(camera_descriptor, index):
    return (
        f"[{index}] {camera_descriptor.display_name} "
        f"vid=0x{camera_descriptor.vendor_id:04x} "
        f"pid=0x{camera_descriptor.product_id:04x} "
        f"bus={camera_descriptor.bus_number} "
        f"addr={camera_descriptor.device_address} "
        f"vc_if={camera_descriptor.interface_number} "
        f"pu={camera_descriptor.processing_unit_id} "
        f"ct={camera_descriptor.camera_terminal_id}"
    )


def _safeGetValue(controller, control_spec, request_code, fallback):
    try:
        raw = controller._getRaw(control_spec, request_code, control_spec["size"])
        return _decodeControlValue(control_spec, raw)
    except UvcControllerError:
        return fallback


def _readUsbString(lib, dev, string_index):
    if string_index <= 0:
        return None

    handle = c_void_p()
    result = lib.libusb_open(dev, byref(handle))
    if result != LIBUSB_SUCCESS:
        return None

    try:
        buffer = (c_uint8 * 256)()
        read_size = lib.libusb_get_string_descriptor_ascii(
            handle,
            c_uint8(string_index),
            cast(buffer, POINTER(c_uint8)),
            256,
        )
        if read_size <= 0:
            return None
        return bytes(buffer[:read_size]).decode("utf-8", errors="replace").strip() or None
    finally:
        lib.libusb_close(handle)


def _findUvcDetails(config_desc):
    for interface_index in range(config_desc.bNumInterfaces):
        interface = config_desc.interface[interface_index]
        for alt_index in range(interface.num_altsetting):
            altsetting = interface.altsetting[alt_index]
            if altsetting.bInterfaceClass == LIBUSB_CLASS_VIDEO and altsetting.bInterfaceSubClass == LIBUSB_SUBCLASS_VIDEO_CONTROL:
                processing_unit_id, camera_terminal_id = _extractUnitIds(altsetting.extra, altsetting.extra_length)
                if processing_unit_id == -1 or camera_terminal_id == -1:
                    processing_unit_id, camera_terminal_id = _extractUnitIds(config_desc.extra, config_desc.extra_length)
                if processing_unit_id != -1 and camera_terminal_id != -1:
                    return int(altsetting.bInterfaceNumber), processing_unit_id, camera_terminal_id
    return None


def _extractUnitIds(extra_ptr, extra_length):
    processing_unit_id = -1
    camera_terminal_id = -1
    if not extra_ptr or extra_length <= 0:
        return processing_unit_id, camera_terminal_id

    raw = ctypes.string_at(extra_ptr, extra_length)
    offset = 0
    while offset + 2 <= len(raw):
        length = raw[offset]
        if length == 0 or offset + length > len(raw):
            break

        if raw[offset + 1] == CS_INTERFACE_DESCRIPTOR_TYPE and length >= 4:
            subtype = raw[offset + 2]
            if subtype == UVC_SUBTYPE_PROCESSING_UNIT:
                processing_unit_id = raw[offset + 3]
            elif subtype == UVC_SUBTYPE_INPUT_TERMINAL and length >= 8:
                terminal_id = raw[offset + 3]
                terminal_type = int.from_bytes(raw[offset + 4 : offset + 6], "little")
                if terminal_type == CAMERA_TERMINAL_TYPE:
                    camera_terminal_id = terminal_id

        offset += length

    return processing_unit_id, camera_terminal_id


def _getControlSpec(control_id):
    if control_id not in CONTROL_SPECS:
        raise UvcControllerError(f"Unknown control: {control_id}")
    return CONTROL_SPECS[control_id]


def _buildWIndex(camera_descriptor, control_spec):
    unit_id = getattr(camera_descriptor, control_spec["unit_key"])
    return ((unit_id & 0xFF) << 8) | (camera_descriptor.interface_number & 0xFF)


def _decodeControlValue(control_spec, raw_bytes):
    kind = control_spec["kind"]
    signed = control_spec.get("signed", False)

    if kind == "pair":
        scale = control_spec.get("scale", 1)
        part_size = control_spec.get("part_size", 4)
        signed = control_spec.get("signed", True)
        first = int.from_bytes(raw_bytes[0:part_size], byteorder="little", signed=signed)
        second = int.from_bytes(raw_bytes[part_size : part_size * 2], byteorder="little", signed=signed)
        return (int(first // scale), int(second // scale))

    if kind == "bool":
        return int.from_bytes(raw_bytes, byteorder="little", signed=False) != 0

    return int.from_bytes(raw_bytes, byteorder="little", signed=signed)


def _encodeControlValue(control_spec, value):
    kind = control_spec["kind"]
    size = control_spec["size"]
    signed = control_spec.get("signed", False)

    if kind == "pair":
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise UvcControllerError("pair control expects (first, second)")
        scale = control_spec.get("scale", 1)
        part_size = control_spec.get("part_size", 4)
        signed_pair = control_spec.get("signed", True)
        first = int(value[0] * scale)
        second = int(value[1] * scale)
        return first.to_bytes(part_size, byteorder="little", signed=signed_pair) + second.to_bytes(
            part_size, byteorder="little", signed=signed_pair
        )

    if kind == "bool":
        number = 1 if bool(value) else 0
        return number.to_bytes(size, byteorder="little", signed=False)

    number = int(value)
    return number.to_bytes(size, byteorder="little", signed=signed)


def _normalizeEnumValue(control_spec, value):
    if isinstance(value, str):
        label_map = {label: enum_value for enum_value, label in control_spec.get("enum_values", [])}
        if value not in label_map:
            raise UvcControllerError(f"invalid enum label: {value}")
        return label_map[value]

    number = int(value)
    allowed_values = {enum_value for enum_value, _ in control_spec.get("enum_values", [])}
    if number not in allowed_values:
        raise UvcControllerError(f"invalid enum value: {number}")
    return number


def _clampIntControl(controller, control_id, value):
    info = controller.getControlInfo(control_id)
    if not info.is_capable:
        raise UvcControllerError("Control not supported by camera")

    clamped_value = min(max(value, info.minimum), info.maximum)
    step = info.resolution if isinstance(info.resolution, int) and info.resolution > 0 else 1
    return info.minimum + ((clamped_value - info.minimum) // step) * step


def _clampPairControl(controller, control_id, value):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise UvcControllerError("pair control expects (first, second)")

    info = controller.getControlInfo(control_id)
    if not info.is_capable:
        raise UvcControllerError("Control not supported by camera")

    minimum = info.minimum
    maximum = info.maximum
    resolution = info.resolution

    out = []
    for idx in (0, 1):
        step = resolution[idx] if resolution[idx] > 0 else 1
        clamped = min(max(int(value[idx]), minimum[idx]), maximum[idx])
        clamped = minimum[idx] + ((clamped - minimum[idx]) // step) * step
        out.append(clamped)
    return (out[0], out[1])


_LIBUSB = None
_LIBUSB_CONTEXT = None


def _getLibusb():
    global _LIBUSB
    if _LIBUSB is not None:
        return _LIBUSB

    lib = ctypes.CDLL(LIBUSB_PATH)
    lib.libusb_init.argtypes = [POINTER(c_void_p)]
    lib.libusb_init.restype = c_int
    lib.libusb_exit.argtypes = [c_void_p]
    lib.libusb_exit.restype = None

    lib.libusb_get_device_list.argtypes = [c_void_p, POINTER(POINTER(c_void_p))]
    lib.libusb_get_device_list.restype = ctypes.c_ssize_t
    lib.libusb_free_device_list.argtypes = [POINTER(c_void_p), c_int]
    lib.libusb_free_device_list.restype = None

    lib.libusb_get_device_descriptor.argtypes = [c_void_p, POINTER(LibusbDeviceDescriptor)]
    lib.libusb_get_device_descriptor.restype = c_int
    lib.libusb_get_bus_number.argtypes = [c_void_p]
    lib.libusb_get_bus_number.restype = c_uint8
    lib.libusb_get_device_address.argtypes = [c_void_p]
    lib.libusb_get_device_address.restype = c_uint8

    lib.libusb_get_active_config_descriptor.argtypes = [c_void_p, POINTER(POINTER(LibusbConfigDescriptor))]
    lib.libusb_get_active_config_descriptor.restype = c_int
    lib.libusb_free_config_descriptor.argtypes = [POINTER(LibusbConfigDescriptor)]
    lib.libusb_free_config_descriptor.restype = None

    lib.libusb_ref_device.argtypes = [c_void_p]
    lib.libusb_ref_device.restype = c_void_p
    lib.libusb_unref_device.argtypes = [c_void_p]
    lib.libusb_unref_device.restype = None

    lib.libusb_open.argtypes = [c_void_p, POINTER(c_void_p)]
    lib.libusb_open.restype = c_int
    lib.libusb_close.argtypes = [c_void_p]
    lib.libusb_close.restype = None
    lib.libusb_get_string_descriptor_ascii.argtypes = [c_void_p, c_uint8, POINTER(c_uint8), c_int]
    lib.libusb_get_string_descriptor_ascii.restype = c_int

    lib.libusb_kernel_driver_active.argtypes = [c_void_p, c_int]
    lib.libusb_kernel_driver_active.restype = c_int
    lib.libusb_detach_kernel_driver.argtypes = [c_void_p, c_int]
    lib.libusb_detach_kernel_driver.restype = c_int
    lib.libusb_claim_interface.argtypes = [c_void_p, c_int]
    lib.libusb_claim_interface.restype = c_int
    lib.libusb_release_interface.argtypes = [c_void_p, c_int]
    lib.libusb_release_interface.restype = c_int

    lib.libusb_control_transfer.argtypes = [
        c_void_p,
        c_uint8,
        c_uint8,
        c_uint16,
        c_uint16,
        POINTER(c_uint8),
        c_uint16,
        c_uint32,
    ]
    lib.libusb_control_transfer.restype = c_int

    _LIBUSB = lib
    return _LIBUSB


def _getLibusbContext():
    global _LIBUSB_CONTEXT
    if _LIBUSB_CONTEXT is not None:
        return _LIBUSB_CONTEXT

    context = c_void_p()
    result = _getLibusb().libusb_init(byref(context))
    if result != LIBUSB_SUCCESS:
        raise UvcControllerError(f"libusb_init failed: {result}")

    _LIBUSB_CONTEXT = context
    return _LIBUSB_CONTEXT


def _shutdownLibusbContext():
    global _LIBUSB_CONTEXT
    if _LIBUSB_CONTEXT is None:
        return
    _getLibusb().libusb_exit(_LIBUSB_CONTEXT)
    _LIBUSB_CONTEXT = None


atexit.register(_shutdownLibusbContext)

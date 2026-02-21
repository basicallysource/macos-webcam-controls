import argparse
import json

from uvc_camera import UvcCameraController, UvcControllerError, formatCamera, listCameras, unrefCamera


def parseArgs():
    parser = argparse.ArgumentParser(description="Apply UVC settings from a config JSON")
    parser.add_argument("config_path", nargs="?", default="config.json", help="path to config.json")
    parser.add_argument("--dry-run", action="store_true", help="show matches and values without writing")
    parser.add_argument("--verbose", action="store_true", help="print control info and read-back values")
    parser.add_argument("--force-manual", action="store_true", help="apply controller.forceManualMode() before settings")
    return parser.parse_args()


def loadConfig(config_path):
    with open(config_path, "r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    cameras_section = payload.get("cameras")
    if not isinstance(cameras_section, list) or not cameras_section:
        raise ValueError("config must include a non-empty 'cameras' list")

    normalized = []
    for item in cameras_section:
        if not isinstance(item, dict):
            raise ValueError("each 'cameras' item must be an object")
        settings = item.get("settings")
        if not isinstance(settings, dict) or not settings:
            raise ValueError("each camera item must include non-empty 'settings' object")

        match = {key: value for key, value in item.items() if key != "settings"}
        if not match:
            raise ValueError("each camera item must include at least one matcher key")

        normalized.append({"match": match, "settings": settings})

    return normalized


def matchesRule(camera, camera_index, rule):
    if "index" in rule and camera_index != int(rule["index"]):
        return False
    if "bus" in rule and camera.bus_number != int(rule["bus"]):
        return False
    if "addr" in rule and camera.device_address != int(rule["addr"]):
        return False
    if "vid" in rule and camera.vendor_id != int(rule["vid"]):
        return False
    if "pid" in rule and camera.product_id != int(rule["pid"]):
        return False

    display_name = camera.display_name.lower()
    if "name" in rule and display_name != str(rule["name"]).lower():
        return False
    if "name_contains" in rule and str(rule["name_contains"]).lower() not in display_name:
        return False

    return True


def resolveTargets(cameras, rules):
    resolved = []
    for rule_index, rule_item in enumerate(rules):
        rule = rule_item["match"]
        matched_indices = []
        for camera_index, camera in enumerate(cameras):
            if matchesRule(camera, camera_index, rule):
                matched_indices.append(camera_index)

        resolved.append(
            {
                "rule_index": rule_index,
                "rule": rule,
                "settings": rule_item["settings"],
                "matched_indices": matched_indices,
            }
        )
    return resolved


def applySettings(cameras, resolved_rules, dry_run, verbose, force_manual):
    had_failures = False

    for resolved in resolved_rules:
        matched_indices = resolved["matched_indices"]
        if not matched_indices:
            print(f"rule {resolved['rule_index']} matched no cameras: {resolved['rule']}")
            had_failures = True
            continue

        for camera_index in matched_indices:
            camera = cameras[camera_index]
            print(f"target {formatCamera(camera, camera_index)}")

            if dry_run:
                for setting_name, setting_value in resolved["settings"].items():
                    print(f"  dry-run {setting_name}={setting_value}")
                continue

            try:
                with UvcCameraController(camera) as controller:
                    if force_manual:
                        try:
                            controller.forceManualMode()
                            print("  force-manual applied")
                        except Exception as exc:
                            print(f"  force-manual failed: {exc}")
                            had_failures = True

                    for setting_name, setting_value in resolved["settings"].items():
                        info = controller.getControlInfo(setting_name)
                        if not info.is_capable:
                            print(f"  skip {setting_name}: not supported")
                            continue
                        if verbose:
                            print(
                                f"  info {setting_name}: kind={info.kind} "
                                f"cur={info.current} min={info.minimum} max={info.maximum} res={info.resolution}"
                            )
                        try:
                            before_value = controller.getControl(setting_name) if verbose else None
                            applied_value = controller.setControl(setting_name, setting_value)
                            after_value = controller.getControl(setting_name)
                            print(f"  set {setting_name}: requested={setting_value} applied={applied_value} read_back={after_value}")
                            if verbose and before_value is not None:
                                print(f"  before {setting_name}={before_value}")
                        except Exception as exc:
                            print(f"  fail {setting_name}: {exc}")
                            had_failures = True
            except UvcControllerError as exc:
                print(f"  fail opening camera: {exc}")
                had_failures = True

    return had_failures


def main():
    args = parseArgs()
    cameras = listCameras()

    try:
        if not cameras:
            print("No UVC webcams found")
            return 1

        rules = loadConfig(args.config_path)
        resolved_rules = resolveTargets(cameras, rules)
        had_failures = applySettings(cameras, resolved_rules, args.dry_run, args.verbose, args.force_manual)
        return 1 if had_failures else 0
    except Exception as exc:
        print(f"error: {exc}")
        return 1
    finally:
        for camera in cameras:
            unrefCamera(camera)


if __name__ == "__main__":
    raise SystemExit(main())

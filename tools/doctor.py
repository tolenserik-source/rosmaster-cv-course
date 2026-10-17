#!/usr/bin/env python3
"""Read-only environment check. Does not open cameras or change ROS settings."""
import argparse
import glob
import importlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Проверка Python, OpenCV и ROS без изменения системы")
    parser.add_argument("--out", default="outputs/environment.json")
    args = parser.parse_args()
    report = {
        "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "machine": platform.machine(),
        "cwd": str(Path.cwd()), "modules": {},
        "ros_environment": {key: os.environ.get(key) for key in
                            ("ROS_VERSION", "ROS_DISTRO", "ROS_PYTHON_VERSION")},
        "commands": {name: shutil.which(name) for name in
                     ("python3", "roscore", "rostopic", "roslaunch", "docker", "jupyter")},
        "video_devices": sorted(glob.glob("/dev/video*")),
        "note": "Devices were listed, not opened. No credentials or tokens are collected."
    }
    for name in ("numpy", "cv2", "rospy", "cv_bridge", "mediapipe"):
        try:
            module = importlib.import_module(name)
            report["modules"][name] = {"available": True, "version": getattr(module, "__version__", None)}
        except Exception as exc:
            report["modules"][name] = {"available": False, "error": str(exc)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, result in report["modules"].items():
        print("{}: {}".format(name, result.get("version") or ("OK" if result["available"] else result["error"])))
    print("Диагностика сохранена: {}".format(out))
    return 0 if all(report["modules"][m]["available"] for m in ("numpy", "cv2")) else 2


if __name__ == "__main__":
    sys.exit(main())

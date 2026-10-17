"""Lesson 9.7: ALVAR environment check and manual quadrilateral geometry."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import numpy as np


def quadrilateral_geometry(corners, image_shape=None):
    points = np.asarray(corners, np.float32).reshape(-1, 2)
    if points.shape != (4, 2) or not np.all(np.isfinite(points)):
        raise ValueError("Provide exactly four finite x,y points in perimeter order")
    if not cv2.isContourConvex(points.reshape(-1, 1, 2)):
        raise ValueError("Corners must form a convex quadrilateral in clockwise/counterclockwise order")
    area = float(cv2.contourArea(points))
    if area < 25:
        raise ValueError("Quadrilateral area must be at least 25 pixels squared")
    if image_shape is not None:
        height, width = image_shape[:2]
        if np.any(points < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] >= height):
            raise ValueError("Corner coordinates must lie inside the image")
    moments = cv2.moments(points)
    center = [float(moments["m10"] / moments["m00"]), float(moments["m01"] / moments["m00"])]
    return {"corners_px": points.tolist(), "centroid_px": center, "area_px2": area,
            "edge_lengths_px": np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1).tolist(),
            "decoded_marker_id": None,
            "note": "Manual geometry only; no ALVAR decoding and no metric pose"}


def diagnose_alvar():
    command = shutil.which("rospack")
    if command is None:
        return {"rospack_available": False, "alvar_package_found": False,
                "next_step": "Use the ROS1 factory environment and source its setup.bash"}
    try:
        result = subprocess.run([command, "find", "ar_track_alvar"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
    except subprocess.TimeoutExpired:
        return {"rospack_available": True, "alvar_package_found": False,
                "next_step": "rospack timed out; check the ROS1 environment"}
    return {"rospack_available": True, "alvar_package_found": result.returncode == 0,
            "package_path": result.stdout.strip() if result.returncode == 0 else None,
            "diagnostic": result.stderr.strip(),
            "next_step": "Read lessons/07_markers.md; this check does not start any camera or robot"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--corners", type=float, nargs=8, metavar="PX")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/07"))
    args = parser.parse_args(argv)
    try:
        if args.diagnose:
            if args.input or args.corners:
                raise ValueError("Choose --diagnose OR --input with --corners")
            data = diagnose_alvar()
            filename = "diagnostic.json"
        else:
            if args.input is None or args.corners is None:
                raise ValueError("Use --diagnose, or --input IMAGE --corners x1 y1 x2 y2 x3 y3 x4 y4")
            image = cv2.imread(str(args.input), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Input image cannot be read")
            data = quadrilateral_geometry(args.corners, image.shape)
            polygon = np.round(data["corners_px"]).astype(np.int32)
            cv2.polylines(image, [polygon], True, (0, 200, 0), 3)
            for index, point in enumerate(polygon):
                cv2.circle(image, tuple(point), 5, (0, 0, 255), -1)
                cv2.putText(image, str(index + 1), tuple(point + [6, -6]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(image, "MANUAL GEOMETRY - NO MARKER ID", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            filename = "geometry.json"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if not args.diagnose and not cv2.imwrite(str(args.output_dir / "geometry.png"), image):
            raise ValueError("Could not save geometry.png")
        with (args.output_dir / filename).open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

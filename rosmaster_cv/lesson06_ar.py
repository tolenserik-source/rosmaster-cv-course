"""Lesson 9.6: planar AR and a separate, genuinely calibrated pose path."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np


def make_checkerboard(columns=7, rows=5, square_pixels=60, perspective=True):
    """Return a synthetic image, never a camera calibration."""
    if columns < 2 or rows < 2 or square_pixels < 10:
        raise ValueError("Need at least 2x2 inner corners and square_pixels >= 10")
    margin = square_pixels
    width = (columns + 3) * square_pixels
    height = (rows + 3) * square_pixels
    image = np.full((height, width, 3), 255, np.uint8)
    for row in range(rows + 1):
        for col in range(columns + 1):
            if (row + col) % 2 == 0:
                x, y = margin + col * square_pixels, margin + row * square_pixels
                image[y:y + square_pixels, x:x + square_pixels] = 0
    if not perspective:
        return image
    source = np.float32([[0, 0], [width - 1, 0],
                         [width - 1, height - 1], [0, height - 1]])
    target = np.float32([[24, 20], [width - 38, 42],
                         [width - 16, height - 28], [38, height - 8]])
    return cv2.warpPerspective(image, cv2.getPerspectiveTransform(source, target),
                               (width, height), borderValue=(255, 255, 255))


def find_board(image, columns=7, rows=5):
    if columns < 2 or rows < 2:
        raise ValueError("columns/rows count INNER corners and must be >= 2")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(
        gray, (columns, rows),
        cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
    if not found:
        raise ValueError("Chessboard not found: check INNER corner counts, focus and full board visibility")
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    return cv2.cornerSubPix(gray, corners, (7, 7), (-1, -1), criteria)


def board_object_points(columns, rows, square_size):
    if not np.isfinite(square_size) or square_size <= 0:
        raise ValueError("square_size must be the measured square side in metres, > 0")
    points = np.zeros((columns * rows, 3), np.float32)
    points[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2)
    return points * float(square_size)


def planar_overlay(image, corners, columns, rows):
    """2D planar overlay: no invented intrinsics and no metric pose."""
    points = np.asarray(corners, np.float32).reshape(-1, 2)
    if len(points) != columns * rows:
        raise ValueError("Unexpected corner count")
    quad = points[[0, columns - 1, columns * rows - 1, (rows - 1) * columns]]
    source = np.float32([[0, 0], [299, 0], [299, 199], [0, 199]])
    homography = cv2.getPerspectiveTransform(source, quad)
    tile = np.full((200, 300, 3), (75, 145, 235), np.uint8)
    cv2.rectangle(tile, (8, 8), (291, 191), (255, 255, 255), 4)
    cv2.putText(tile, "ROSMASTER CV", (21, 85), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(tile, "2D PLANAR OVERLAY", (18, 130), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1, cv2.LINE_AA)
    size = (image.shape[1], image.shape[0])
    warped = cv2.warpPerspective(tile, homography, size)
    mask = cv2.warpPerspective(np.full((200, 300), 255, np.uint8), homography,
                               size, flags=cv2.INTER_NEAREST)
    result = image.copy()
    blended = cv2.addWeighted(image, 0.3, warped, 0.7, 0)
    result[mask > 0] = blended[mask > 0]
    cv2.polylines(result, [np.round(quad).astype(np.int32)], True, (0, 220, 0), 2)
    return result, homography


def load_calibration(path, image_size):
    with open(str(path), encoding="utf-8") as stream:
        data = json.load(stream)
    matrix = np.asarray(data.get("camera_matrix"), np.float64)
    distortion = np.asarray(data.get("distortion_coefficients"), np.float64)
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        raise ValueError("Calibration camera_matrix must be finite 3x3")
    if matrix[0, 0] <= 0 or matrix[1, 1] <= 0 or not np.allclose(matrix[2], [0, 0, 1]):
        raise ValueError("Invalid camera intrinsic matrix")
    if distortion.size not in (4, 5, 8, 12, 14) or not np.all(np.isfinite(distortion)):
        raise ValueError("Expected 4/5/8/12/14 finite OpenCV distortion coefficients")
    if list(data.get("image_size", [])) != list(image_size):
        raise ValueError("Image resolution differs from calibration; use the calibrated resolution")
    return matrix, distortion.reshape(-1, 1)


def calibrated_pose(image, corners, columns, rows, square_size, calibration_path):
    camera, distortion = load_calibration(calibration_path, (image.shape[1], image.shape[0]))
    objects = board_object_points(columns, rows, square_size)
    ok, rvec, tvec = cv2.solvePnP(objects, corners, camera, distortion,
                                flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok or not np.all(np.isfinite(tvec)):
        raise ValueError("solvePnP failed")
    projected, _ = cv2.projectPoints(objects, rvec, tvec, camera, distortion)
    rms = float(np.sqrt(np.mean(np.sum((projected - corners) ** 2, axis=2))))
    result = image.copy()
    cv2.drawChessboardCorners(result, (columns, rows), corners, True)
    cv2.drawFrameAxes(result, camera, distortion, rvec, tvec, float(square_size) * 2)
    return result, {"method": "calibrated_solvePnP", "rvec_rad": rvec.reshape(-1).tolist(),
                    "tvec_m": tvec.reshape(-1).tolist(), "reprojection_rms_px": rms,
                    "pose_frame": "board origin at first detected inner corner, expressed in camera frame",
                    "note": "Metric scale depends on actual calibration and measured square side"}


def calibrate_directory(directory, columns, rows, square_size):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("Calibration directory does not exist")
    files = sorted(p for p in directory.iterdir()
                   if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"))
    objects, images, accepted, rejected = [], [], [], []
    size = None
    template = board_object_points(columns, rows, square_size)
    for path in files:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            rejected.append(path.name)
            continue
        current_size = (image.shape[1], image.shape[0])
        if size is not None and current_size != size:
            raise ValueError("All calibration images must have the same resolution")
        try:
            corners = find_board(image, columns, rows)
        except ValueError:
            rejected.append(path.name)
            continue
        size = current_size
        images.append(corners)
        objects.append(template.copy())
        accepted.append(path.name)
    if len(images) < 10:
        raise ValueError("Need >= 10 real, varied board views with detected corners; found {}".format(len(images)))
    rms, camera, distortion, rvecs, tvecs = cv2.calibrateCamera(objects, images, size, None, None)
    if not np.isfinite(rms) or not np.all(np.isfinite(camera)) or not np.all(np.isfinite(distortion)):
        raise ValueError("Calibration failed: non-finite parameters")
    errors = []
    for obj, observed, rv, tv in zip(objects, images, rvecs, tvecs):
        projected, _ = cv2.projectPoints(obj, rv, tv, camera, distortion)
        errors.append(float(np.sqrt(np.mean(np.sum((projected - observed) ** 2, axis=2)))))
    return {"camera_matrix": camera.tolist(), "distortion_coefficients": distortion.reshape(-1).tolist(),
            "image_size": list(size), "square_size_m": float(square_size),
            "columns": columns, "rows": rows, "rms_px": float(rms),
            "per_view_rms_px": errors, "images": accepted, "rejected_images": rejected,
            "warning": "A low calibration RMS alone does not establish metric accuracy"}


def write_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise ValueError("Cannot write image: {}".format(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", action="store_true")
    source.add_argument("--board-template", action="store_true", help="Flat board to print, then measure physically")
    source.add_argument("--input", type=Path)
    source.add_argument("--calibrate-dir", type=Path)
    parser.add_argument("--columns", type=int, default=7, help="Inner corners per row")
    parser.add_argument("--rows", type=int, default=5, help="Inner corners per column")
    parser.add_argument("--square-size", type=float, help="Measured square side in metres")
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/06"))
    args = parser.parse_args(argv)
    try:
        if args.columns < 2 or args.rows < 2:
            raise ValueError("columns/rows must be >= 2")
        if (args.calibrate_dir or args.calibration) and args.square_size is None:
            raise ValueError("Calibration and metric AR require --square-size (measured metres)")
        if (args.synthetic or args.board_template) and (args.calibration or args.square_size is not None):
            raise ValueError("Synthetic mode illustrates 2D geometry; do not assign it a real camera calibration")
        if args.calibrate_dir and args.calibration:
            raise ValueError("Use --calibrate-dir to create a calibration, or --calibration to apply one")
        if args.board_template:
            image = make_checkerboard(args.columns, args.rows, perspective=False)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            write_image(args.output_dir / "checkerboard_template.png", image)
            data = {"method": "flat_printable_template", "columns": args.columns, "rows": args.rows,
                    "note": "Print on a flat board and measure actual square side; image has no guaranteed print scale"}
            output = args.output_dir / "template.json"
        elif args.calibrate_dir:
            data = calibrate_directory(args.calibrate_dir, args.columns, args.rows, args.square_size)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            output = args.output_dir / "calibration.json"
        else:
            image = make_checkerboard(args.columns, args.rows) if args.synthetic else cv2.imread(str(args.input))
            if image is None:
                raise ValueError("Input image cannot be read: {}".format(args.input))
            corners = find_board(image, args.columns, args.rows)
            if args.calibration:
                result, data = calibrated_pose(image, corners, args.columns, args.rows,
                                                args.square_size, args.calibration)
            else:
                result, homography = planar_overlay(image, corners, args.columns, args.rows)
                data = {"method": "2D_homography", "homography": homography.tolist(),
                        "metric_pose_available": False, "inner_corners_found": len(corners)}
            args.output_dir.mkdir(parents=True, exist_ok=True)
            write_image(args.output_dir / "checkerboard.png", image)
            write_image(args.output_dir / "ar_overlay.png", result)
            output = args.output_dir / "result.json"
        with output.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print("Saved: {}".format(output))
        return 0
    except (ValueError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

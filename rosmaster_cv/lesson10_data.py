"""Lesson 9.10: LaserScan to raster, PointCloud2/ASCII PCD and rigid transforms."""
import argparse
import itertools
import json
from pathlib import Path
import sys
import threading

import cv2
import numpy as np
from .ros_deadline import run_with_deadline


def scan_to_points(ranges, angle_min, angle_increment, range_min, range_max):
    values = np.asarray(ranges, np.float64)
    scalars = np.asarray([angle_min, angle_increment, range_min, range_max], np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(scalars)):
        raise ValueError("Scan ranges must be 1D and scan parameters finite")
    if angle_increment == 0 or range_min < 0 or range_max <= range_min:
        raise ValueError("Invalid scan angular increment or range limits")
    angles = angle_min + np.arange(len(values)) * angle_increment
    valid = np.isfinite(values) & (values >= range_min) & (values <= range_max) & (values > 0)
    return np.column_stack((values[valid] * np.cos(angles[valid]),
                            values[valid] * np.sin(angles[valid]),
                            np.zeros(np.count_nonzero(valid))))


def transform_points(points, matrix):
    points = np.asarray(points, np.float64)
    matrix = np.asarray(matrix, np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
        raise ValueError("Points must be a finite Nx3 array")
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("Transform must be a finite 4x4 matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-7):
        raise ValueError("Invalid homogeneous transform bottom row")
    rotation = matrix[:3, :3]
    if (not np.allclose(rotation.T.dot(rotation), np.eye(3), atol=1e-5)
            or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-5)):
        raise ValueError("Transform rotation must be orthonormal with determinant +1; no scale/reflection")
    return points.dot(rotation.T) + matrix[:3, 3]


def rasterize(points, extent=5.0, size=600):
    """Top-down view: x points upward and y points leftward on the page."""
    points = np.asarray(points, np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
        raise ValueError("Expected finite Nx3 points")
    if not np.isfinite(extent) or extent <= 0 or size < 100 or size > 4000:
        raise ValueError("extent must be positive and raster size in [100, 4000]")
    image = np.full((size, size, 3), 250, np.uint8)
    center = (size - 1) / 2.0
    scale = center / float(extent)
    inside = (np.abs(points[:, 0]) <= extent) & (np.abs(points[:, 1]) <= extent)
    visible = points[inside]
    pixels = np.column_stack((center - visible[:, 1] * scale,
                              center - visible[:, 0] * scale))
    pixels = np.rint(pixels).astype(np.int32)
    origin = int(round(center))
    cv2.line(image, (origin, 12), (origin, size - 12), (210, 210, 210), 1)
    cv2.line(image, (12, origin), (size - 12, origin), (210, 210, 210), 1)
    for pixel in pixels:
        cv2.circle(image, tuple(pixel), 2, (160, 75, 25), -1)
    cv2.circle(image, (origin, origin), 5, (0, 0, 230), -1)
    cv2.putText(image, "+x", (origin + 7, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
    cv2.putText(image, "+y", (12, origin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
    cv2.putText(image, "extent +/- {:.2f} m; TOP VIEW".format(extent), (10, size - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1)
    return image, int(np.count_nonzero(~inside))


def read_ascii_pcd(path, max_points=200000):
    """Read x/y/z from DATA ascii PCD. Reject unsupported binary explicitly."""
    header = {}
    with open(str(path), encoding="ascii") as stream:
        for line in stream:
            parts = line.strip().split()
            if not parts or parts[0].startswith("#"):
                continue
            key = parts[0].upper()
            header[key] = parts[1:]
            if key == "DATA":
                break
        if header.get("DATA") != ["ascii"]:
            raise ValueError("Only PCD DATA ascii is supported; convert binary with PCL separately")
        fields = header.get("FIELDS", header.get("FIELD", []))
        if any(name not in fields for name in ("x", "y", "z")):
            raise ValueError("PCD must contain x, y, z fields")
        counts = [int(v) for v in header.get("COUNT", ["1"] * len(fields))]
        if len(counts) != len(fields) or any(c <= 0 for c in counts):
            raise ValueError("Invalid PCD COUNT")
        offsets = np.cumsum([0] + counts[:-1]).tolist()
        coordinates = [offsets[fields.index(name)] for name in ("x", "y", "z")]
        if any(counts[fields.index(name)] != 1 for name in ("x", "y", "z")):
            raise ValueError("PCD x/y/z must each have COUNT 1")
        result = []
        for line in itertools.islice(stream, max_points):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != sum(counts):
                raise ValueError("PCD data row has unexpected field count")
            xyz = [float(parts[i]) for i in coordinates]
            if np.all(np.isfinite(xyz)):
                result.append(xyz)
    return np.asarray(result, np.float64).reshape(-1, 3)


def write_ascii_pcd(path, points):
    points = np.asarray(points, np.float64)
    with open(str(path), "w", encoding="ascii") as stream:
        stream.write("# Synthetic teaching data; coordinate values in metres\n")
        stream.write("VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n")
        stream.write("WIDTH {}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\n".format(len(points)))
        stream.write("POINTS {}\nDATA ascii\n".format(len(points)))
        np.savetxt(stream, points, fmt="%.7f")


def get_ros_points(topic, kind, timeout, max_points):
    try:
        import rospy
        from sensor_msgs.msg import LaserScan, PointCloud2
        from sensor_msgs import point_cloud2
    except ImportError as exc:
        raise RuntimeError("Use the factory ROS1 Python environment: {}".format(exc))
    try:
        rospy.init_node("course_spatial_data", anonymous=True, disable_signals=True)
    except Exception as exc:
        raise RuntimeError("Cannot initialize ROS1 node: {}".format(exc))
    event, messages = threading.Event(), []

    def callback(message):
        if not event.is_set():
            messages.append(message)
            event.set()

    message_type = LaserScan if kind == "scan" else PointCloud2
    subscriber = rospy.Subscriber(topic, message_type, callback, queue_size=1, buff_size=2 ** 26)
    try:
        if not event.wait(timeout):
            raise RuntimeError("No {} received from {} within {} seconds".format(kind, topic, timeout))
        message = messages[0]
        metadata = {"topic": topic, "source_frame": message.header.frame_id,
                    "stamp_secs": message.header.stamp.secs, "stamp_nsecs": message.header.stamp.nsecs}
        if kind == "scan":
            points = scan_to_points(message.ranges, message.angle_min, message.angle_increment,
                                     message.range_min, message.range_max)
            metadata["rays_received"] = len(message.ranges)
            metadata["unit_basis"] = "sensor_msgs/LaserScan specifies ranges in metres"
        else:
            generator = point_cloud2.read_points(message, field_names=("x", "y", "z"), skip_nans=True)
            rows = list(itertools.islice(generator, max_points))
            points = np.asarray(rows, np.float64).reshape(-1, 3)
            points = points[np.all(np.isfinite(points), axis=1)]
            metadata["points_available"] = message.width * message.height
            metadata["point_limit"] = max_points
            metadata["unit_basis"] = "ROS REP-103 uses metres; confirm the publishing driver's convention"
        return points, metadata
    finally:
        subscriber.unregister()
        rospy.signal_shutdown("One spatial message received or timeout")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", action="store_true")
    source.add_argument("--scan-topic")
    source.add_argument("--cloud-topic")
    source.add_argument("--pcd", type=Path)
    source.add_argument("--input-json", type=Path, help="LaserScan fields as JSON")
    parser.add_argument("--pcd-units", choices=("m",), help="Required acknowledgement for your PCD")
    parser.add_argument("--transform-json", type=Path, help="Known T_target_source, never guessed")
    parser.add_argument("--extent", type=float, default=5.0)
    parser.add_argument("--size", type=int, default=600)
    parser.add_argument("--max-points", type=int, default=200000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/10"))
    args = parser.parse_args(argv)
    try:
        if args.max_points < 1 or args.max_points > 2000000:
            raise ValueError("--max-points must be in [1, 2000000]")
        if not np.isfinite(args.timeout) or not 0 < args.timeout <= 300:
            raise ValueError("--timeout must be in (0, 300]")
        metadata = {"units": "m", "source_frame": "unspecified"}
        extra_cloud = None
        if args.synthetic:
            angles = np.linspace(-np.pi, np.pi, 361)
            ranges = 3.0 + 0.5 * np.sin(3 * angles)
            ranges[::31] = np.nan
            points = scan_to_points(ranges, -np.pi, 2 * np.pi / 360, 0.1, 8.0)
            grid_x, grid_y = np.meshgrid(np.linspace(-2, 2, 35), np.linspace(-1.5, 1.5, 25))
            extra_cloud = np.column_stack((grid_x.ravel(), grid_y.ravel(),
                                           0.3 + 0.1 * grid_x.ravel()))
            metadata.update({"source": "synthetic LaserScan, NOT robot observations",
                              "source_frame": "synthetic_scan", "rays_received": len(ranges)})
        elif args.scan_topic or args.cloud_topic:
            topic = args.scan_topic or args.cloud_topic
            if not topic.strip():
                raise ValueError("ROS topic cannot be empty")
            points, ros_metadata = run_with_deadline(
                get_ros_points, (topic, "scan" if args.scan_topic else "cloud", args.timeout,
                                 args.max_points), args.timeout)
            metadata.update(ros_metadata)
        elif args.pcd:
            if args.pcd_units != "m":
                raise ValueError("PCD stores no universal unit: verify it and supply --pcd-units m")
            points = read_ascii_pcd(args.pcd, args.max_points)
            metadata.update({"source": str(args.pcd), "units_confirmed_by_user": True,
                              "point_limit": args.max_points})
        else:
            with args.input_json.open(encoding="utf-8") as stream:
                scan = json.load(stream)
            required = ("ranges", "angle_min", "angle_increment", "range_min", "range_max")
            if any(name not in scan for name in required):
                raise ValueError("Scan JSON needs: {}".format(", ".join(required)))
            values = [np.nan if value is None else value for value in scan["ranges"]]
            points = scan_to_points(values, scan["angle_min"], scan["angle_increment"],
                                     scan["range_min"], scan["range_max"])
            metadata.update({"source": str(args.input_json),
                              "source_frame": scan.get("frame_id", "unspecified"),
                              "unit_basis": "Course JSON uses radians and metres"})
        if len(points) == 0:
            raise ValueError("No finite points within the sensor's valid range")
        if args.transform_json:
            with args.transform_json.open(encoding="utf-8") as stream:
                transform = json.load(stream)
            if not transform.get("source_frame") or not transform.get("target_frame"):
                raise ValueError("Transform JSON needs source_frame, target_frame, matrix")
            if (metadata["source_frame"] != "unspecified"
                    and transform["source_frame"] != metadata["source_frame"]):
                raise ValueError("Transform source_frame does not match the data frame")
            points = transform_points(points, transform.get("matrix"))
            metadata["transform"] = transform
            metadata["result_frame"] = transform["target_frame"]
        image, clipped = rasterize(points, args.extent, args.size)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        np.save(str(args.output_dir / "points.npy"), points, allow_pickle=False)
        if not cv2.imwrite(str(args.output_dir / "top_view.png"), image):
            raise ValueError("Cannot save top_view.png")
        if extra_cloud is not None:
            write_ascii_pcd(args.output_dir / "synthetic_cloud.pcd", extra_cloud)
            scan_json = {"angle_min": -float(np.pi), "angle_increment": 2 * float(np.pi) / 360,
                         "range_min": 0.1, "range_max": 8.0, "frame_id": "synthetic_scan",
                         "ranges": [float(v) if np.isfinite(v) else None for v in ranges]}
            with (args.output_dir / "synthetic_scan.json").open("w", encoding="utf-8") as stream:
                json.dump(scan_json, stream, indent=2, allow_nan=False)
            angle = np.pi / 2
            demo = [[float(np.cos(angle)), -float(np.sin(angle)), 0, 0],
                    [float(np.sin(angle)), float(np.cos(angle)), 0, 0],
                    [0, 0, 1, 0], [0, 0, 0, 1]]
            with (args.output_dir / "synthetic_rotation.json").open("w", encoding="utf-8") as stream:
                json.dump({"source_frame": "synthetic_scan", "target_frame": "synthetic_rotated",
                           "matrix": demo, "note": "Teaching example only; NOT robot extrinsics"}, stream, indent=2)
        metadata.update({"valid_points": len(points), "points_outside_raster": clipped,
                          "raster_extent_m": args.extent, "raster_axis_mapping": "+x up; +y left",
                          "note": "A top-down projection loses z; this output is not a map or a SLAM result"})
        with (args.output_dir / "metadata.json").open("w", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, TypeError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

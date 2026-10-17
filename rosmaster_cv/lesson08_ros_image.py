"""Lesson 9.8: save one selected ROS1 Image without a graphical window."""
import argparse
import json
from pathlib import Path
import sys
import threading

import cv2
import numpy as np
from .ros_deadline import run_with_deadline


def image_preview(array):
    """Display-only preview; the original physical data is saved separately."""
    image = np.asarray(array)
    if image.dtype == np.uint8 and image.ndim in (2, 3):
        return image.copy()
    if image.ndim != 2:
        raise ValueError("Preview expects a 2D depth/mono array or an 8-bit image")
    valid = np.isfinite(image) & (image > 0)
    result = np.zeros(image.shape, np.uint8)
    if np.any(valid):
        low, high = np.percentile(image[valid], [2, 98])
        if high > low:
            result[valid] = np.clip((image[valid].astype(np.float64) - low) * 255.0 /
                                    (high - low), 0, 255).astype(np.uint8)
        else:
            result[valid] = 180
    return result


def save_converted_image(array, output, source_encoding, passthrough=False,
                         invert=False, header=None):
    output = Path(output)
    image = np.asarray(array)
    if image.size == 0:
        raise ValueError("Received an empty image")
    if output.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise ValueError("--output must be a PNG/JPG preview path; passthrough also saves .npy")
    if invert and (image.dtype != np.uint8 or image.ndim not in (2, 3)):
        raise ValueError("--invert applies only to 8-bit images, never to depth values")
    output.parent.mkdir(parents=True, exist_ok=True)
    preview = image_preview(image)
    if invert:
        preview = 255 - preview
    if passthrough and source_encoding == "rgb8":
        preview = cv2.cvtColor(preview, cv2.COLOR_RGB2BGR)
    elif passthrough and source_encoding == "rgba8":
        preview = cv2.cvtColor(preview, cv2.COLOR_RGBA2BGRA)
    if not cv2.imwrite(str(output), preview):
        raise ValueError("Could not write preview")
    data = {"source_encoding": source_encoding, "shape": list(image.shape),
            "dtype": str(image.dtype), "conversion": "passthrough" if passthrough else "bgr8",
            "preview_inverted": bool(invert), "header": header or {},
            "physical_unit": "not inferred; verify the publishing driver and topic documentation"}
    if passthrough:
        raw_path = output.with_suffix(".npy")
        np.save(str(raw_path), image, allow_pickle=False)
        data["raw_array"] = str(raw_path)
        data["preview_note"] = "Non-uint8 data is normalized for viewing; do calculations on the NPY array"
    metadata = output.with_suffix(".json")
    with metadata.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return data


def capture_one(topic, timeout, encoding):
    try:
        import rospy
        from sensor_msgs.msg import Image
        from cv_bridge import CvBridge
    except ImportError as exc:
        raise RuntimeError("ROS1 rospy/cv_bridge are unavailable. Run in the factory ROS1 Python environment: {}".format(exc))
    try:
        rospy.init_node("course_save_image", anonymous=True, disable_signals=True)
    except Exception as exc:
        raise RuntimeError("Cannot initialize ROS1 node; check the environment and ROS master: {}".format(exc))
    arrived = threading.Event()
    received = []

    def callback(message):
        if not arrived.is_set():
            received.append(message)
            arrived.set()

    subscription = rospy.Subscriber(topic, Image, callback, queue_size=1, buff_size=2 ** 24)
    try:
        if not arrived.wait(timeout):
            raise RuntimeError("No sensor_msgs/Image on {} within {} wall-clock seconds".format(topic, timeout))
        message = received[0]
        try:
            array = CvBridge().imgmsg_to_cv2(message, desired_encoding=encoding)
        except Exception as exc:
            raise RuntimeError("cv_bridge cannot convert {} to {}: {}".format(message.encoding, encoding, exc))
        header = {"frame_id": message.header.frame_id, "stamp_secs": message.header.stamp.secs,
                  "stamp_nsecs": message.header.stamp.nsecs}
        return array, message.encoding, header
    finally:
        subscription.unregister()
        rospy.signal_shutdown("One image received or timeout")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, help="Existing raw sensor_msgs/Image topic")
    parser.add_argument("--encoding", choices=("bgr8", "passthrough"), default="bgr8")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--invert", action="store_true", help="Invert 8-bit preview only")
    parser.add_argument("--output", type=Path, default=Path("outputs/08/frame.png"))
    args = parser.parse_args(argv)
    try:
        if not args.topic.strip() or not np.isfinite(args.timeout) or not 0 < args.timeout <= 300:
            raise ValueError("--topic cannot be empty; --timeout must be in (0, 300] seconds")
        array, encoding, header = run_with_deadline(capture_one,
                                                     (args.topic, args.timeout, args.encoding),
                                                     args.timeout)
        data = save_converted_image(array, args.output, encoding, args.encoding == "passthrough",
                                     args.invert, header)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

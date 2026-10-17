"""Lesson 9.9: bounded ROS1 red-mask processing; publishes images only."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

import cv2
import numpy as np
from .ros_deadline import run_with_deadline


def red_mask(bgr):
    image = np.asarray(bgr)
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("red_mask expects a uint8 BGR image with 3 channels")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    low = cv2.inRange(hsv, np.uint8([0, 100, 80]), np.uint8([10, 255, 255]))
    high = cv2.inRange(hsv, np.uint8([170, 100, 80]), np.uint8([179, 255, 255]))
    return cv2.bitwise_or(low, high)


def run_node(topic, output_topic, seconds, output_dir):
    try:
        import rospy
        from sensor_msgs.msg import Image
        from cv_bridge import CvBridge
    except ImportError as exc:
        raise RuntimeError("Use the factory ROS1 environment with rospy and cv_bridge: {}".format(exc))
    try:
        rospy.init_node("course_red_mask", anonymous=True, disable_signals=True)
    except Exception as exc:
        raise RuntimeError("Cannot initialize ROS1; check ROS master: {}".format(exc))
    if rospy.resolve_name(topic) == rospy.resolve_name(output_topic):
        raise ValueError("Input and output topics must be different")
    bridge = CvBridge()
    publisher = rospy.Publisher(output_topic, Image, queue_size=1)
    state = {"frames_received": 0, "frames_processed": 0, "conversion_errors": 0,
             "last_error": None, "last_red_fraction": None}
    lock = threading.Lock()
    last_mask = [None]

    def callback(message):
        with lock:
            state["frames_received"] += 1
        try:
            image = bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
            mask = red_mask(image)
            output = bridge.cv2_to_imgmsg(mask, encoding="mono8")
            output.header = message.header
            publisher.publish(output)
            with lock:
                state["frames_processed"] += 1
                state["last_red_fraction"] = float(np.count_nonzero(mask)) / mask.size
                state["last_frame_id"] = message.header.frame_id
                last_mask[0] = mask.copy()
        except Exception as exc:
            with lock:
                state["conversion_errors"] += 1
                state["last_error"] = str(exc)

    subscriber = rospy.Subscriber(topic, Image, callback, queue_size=1, buff_size=2 ** 24)
    start = time.monotonic()
    wait_event = threading.Event()
    try:
        while not rospy.is_shutdown() and time.monotonic() - start < seconds:
            wait_event.wait(min(0.1, max(0.0, seconds - (time.monotonic() - start))))
    finally:
        subscriber.unregister()
        rospy.signal_shutdown("Bounded lesson complete")
    with lock:
        data = dict(state)
        mask = None if last_mask[0] is None else last_mask[0].copy()
    data.update({"input_topic": topic, "output_topic": output_topic,
                 "elapsed_wall_seconds": time.monotonic() - start,
                 "header_policy": "input header preserved", "output_encoding": "mono8"})
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if mask is not None and not cv2.imwrite(str(output_dir / "last_mask.png"), mask):
        raise ValueError("Cannot save last_mask.png")
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
    if data["frames_processed"] == 0:
        raise RuntimeError("No images processed; inspect outputs/09/metrics.json (or your output directory)")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output-topic", default="/course/red_mask")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/09"))
    args = parser.parse_args(argv)
    try:
        if not args.topic.strip():
            raise ValueError("--topic cannot be empty")
        if not args.output_topic.startswith("/course/") or args.output_topic == args.topic:
            raise ValueError("Use a distinct output image topic under /course/")
        if not np.isfinite(args.seconds) or not 0 < args.seconds <= 3600:
            raise ValueError("--seconds must be in (0, 3600]")
        data = run_with_deadline(run_node,
                                 (args.topic, args.output_topic, args.seconds, args.output_dir),
                                 args.seconds + 10.0)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Lesson 9.11: hands, pose or face landmarks with explicit MediaPipe backend."""
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np


HAND_EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
              (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14),
              (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20))
POSE_EDGES = ((11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23),
              (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28),
              (27, 29), (29, 31), (28, 30), (30, 32))


def make_detector(backend, mode, model=None):
    if backend == "tasks" and (model is None or not Path(model).is_file()):
        raise ValueError("Tasks needs --model /path/to/the matching official .task model")
    try:
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError("MediaPipe is not installed in this interpreter. Use the lesson's isolated laptop environment or existing factory legacy environment: {}".format(exc))
    if backend == "tasks":
        if not hasattr(mp, "tasks"):
            raise RuntimeError("This MediaPipe installation has no Tasks API; select an appropriate environment")
        names = {"hands": "HandLandmarker", "pose": "PoseLandmarker", "face": "FaceLandmarker"}
        detector_class = getattr(mp.tasks.vision, names[mode], None)
        if detector_class is None:
            raise RuntimeError("This MediaPipe version does not provide {}".format(names[mode]))
        try:
            detector = detector_class.create_from_model_path(str(model))
        except Exception as exc:
            raise RuntimeError("Cannot create Tasks detector; check model/task match and platform support: {}".format(exc))
    else:
        if not hasattr(mp, "solutions"):
            raise RuntimeError("This installation has no mp.solutions. Use --backend tasks with its .task model; do not upgrade a factory environment")
        if mode == "hands":
            detector = mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=2,
                                               min_detection_confidence=0.5)
        elif mode == "pose":
            detector = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1,
                                             min_detection_confidence=0.5)
        else:
            detector = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=2,
                                                        min_detection_confidence=0.5)
    return mp, detector


def landmarks_from_result(result, backend, mode):
    if backend == "tasks":
        name = {"hands": "hand_landmarks", "pose": "pose_landmarks", "face": "face_landmarks"}[mode]
        groups = getattr(result, name, None) or []
    elif mode == "pose":
        pose = getattr(result, "pose_landmarks", None)
        groups = [pose.landmark] if pose is not None else []
    else:
        name = "multi_hand_landmarks" if mode == "hands" else "multi_face_landmarks"
        groups = [group.landmark for group in (getattr(result, name, None) or [])]
    serialized = []
    for group in groups:
        points = []
        for landmark in group:
            point = {"x": float(landmark.x), "y": float(landmark.y), "z": float(landmark.z)}
            for key in ("visibility", "presence"):
                value = getattr(landmark, key, None)
                if value is not None:
                    point[key] = float(value)
            if all(np.isfinite(value) for value in point.values()):
                points.append(point)
            else:
                points.append(None)
        serialized.append(points)
    return serialized


def annotate_landmarks(image, groups, mode):
    result = image.copy()
    height, width = result.shape[:2]
    edges = HAND_EDGES if mode == "hands" else POSE_EDGES if mode == "pose" else ()
    for group in groups:
        pixels = []
        for landmark in group:
            if landmark is None:
                pixels.append(None)
                continue
            x, y = landmark["x"], landmark["y"]
            if not (0 <= x <= 1 and 0 <= y <= 1):
                pixels.append(None)
                continue
            pixels.append((min(width - 1, int(round(x * width))),
                           min(height - 1, int(round(y * height)))))
        for a, b in edges:
            if a < len(pixels) and b < len(pixels) and pixels[a] is not None and pixels[b] is not None:
                cv2.line(result, pixels[a], pixels[b], (60, 210, 60), 2)
        for pixel in pixels:
            if pixel is not None:
                cv2.circle(result, pixel, 2 if mode == "face" else 3, (0, 80, 255), -1)
    cv2.putText(result, "{}: {} detection(s)".format(mode, len(groups)), (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 160, 0), 2)
    return result


def process_frame(mp, detector, image, backend, mode):
    rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if backend == "tasks":
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    else:
        result = detector.process(rgb)
    groups = landmarks_from_result(result, backend, mode)
    return annotate_landmarks(image, groups, mode), groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="A real image, e.g. the saved ROS RGB frame")
    source.add_argument("--camera", type=int, help="Local camera index; prefer saved ROS frames on the robot")
    parser.add_argument("--mode", choices=("hands", "pose", "face"), default="hands")
    parser.add_argument("--backend", choices=("tasks", "legacy"), default="tasks")
    parser.add_argument("--model", type=Path, help="Official model matching the selected Tasks detector")
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/11"))
    args = parser.parse_args(argv)
    camera, detector = None, None
    try:
        if not 1 <= args.frames <= 1000 or not np.isfinite(args.seconds) or not 0 < args.seconds <= 300:
            raise ValueError("--frames must be in [1, 1000]; --seconds in (0, 300]")
        if args.camera is not None and args.camera < 0:
            raise ValueError("--camera must be a nonnegative device index")
        if args.backend == "legacy" and args.model is not None:
            raise ValueError("--model is for Tasks only; legacy uses models from its installed environment")
        image = None
        if args.input:
            image = cv2.imread(str(args.input), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Cannot read your input image: {}".format(args.input))
        mp, detector = make_detector(args.backend, args.mode, args.model)
        if args.camera is not None:
            camera = cv2.VideoCapture(args.camera)
            if not camera.isOpened():
                raise RuntimeError("Cannot open camera; check index and whether the ROS driver owns it")
        started = time.monotonic()
        records, annotated = [], None
        for frame_number in range(args.frames if camera is not None else 1):
            if time.monotonic() - started >= args.seconds:
                break
            if camera is not None:
                ok, image = camera.read()
                if not ok or image is None:
                    raise RuntimeError("Camera did not return a frame")
            before = time.monotonic()
            annotated, landmarks = process_frame(mp, detector, image, args.backend, args.mode)
            records.append({"frame": frame_number, "inference_ms": (time.monotonic() - before) * 1000,
                            "detections": len(landmarks), "landmarks": landmarks})
        if not records:
            raise RuntimeError("No frames processed within the selected limit")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(args.output_dir / "landmarks.png"), annotated):
            raise ValueError("Could not save landmarks.png")
        data = {"backend": args.backend, "mode": args.mode,
                "mediapipe_version": getattr(mp, "__version__", "unknown"),
                "model": str(args.model) if args.model else "installed legacy model",
                "image_size": [image.shape[1], image.shape[0]],
                "processed_frames": len(records), "records": records,
                "processing": "Each frame is processed independently in IMAGE/static mode",
                "coordinate_note": "x/y are normalized image coordinates; z is model-specific relative depth, NOT measured metres",
                "annotation_note": "Face draws landmark dots; hands/pose use selected anatomical connections"}
        with (args.output_dir / "landmarks.json").open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print("Saved {} frame(s); last frame detections: {}. Output: {}".format(
            len(records), records[-1]["detections"], args.output_dir))
        return 0
    except (ValueError, RuntimeError, OSError, cv2.error) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2
    finally:
        if camera is not None:
            camera.release()
        if detector is not None:
            detector.close()


if __name__ == "__main__":
    sys.exit(main())

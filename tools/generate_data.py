#!/usr/bin/env python3
"""Создать собственные учебные изображения и видео строго в каталоге курса data/."""

import argparse
import math
from pathlib import Path
import sys
import cv2
import numpy as np

COURSE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COURSE_ROOT))
from rosmaster_cv.common import ensure_out, save_image, save_json
from rosmaster_cv.lesson02_geometry import PLANE_CORNERS


def color_from_hsv(hue, saturation=220, value=225):
    pixel = np.array([[[hue, saturation, value]]], dtype=np.uint8)
    return tuple(int(v) for v in cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)[0, 0])


def make_scene():
    image = np.full((600, 800, 3), (54, 49, 44), dtype=np.uint8)
    for x in range(0, 800, 40):
        cv2.line(image, (x, 0), (x, 599), (64, 59, 54), 1)
    for y in range(0, 600, 40):
        cv2.line(image, (0, y), (799, y), (64, 59, 54), 1)
    cv2.putText(image, "ROBOT VISION / ORIGINAL TEST SCENE", (35, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.83, (235, 235, 235), 2, cv2.LINE_AA)
    cv2.circle(image, (160, 200), 70, color_from_hsv(2), -1)
    polygon = np.int32([[370, 125], [505, 160], [470, 280], [345, 245]])
    cv2.fillConvexPoly(image, polygon, color_from_hsv(175))
    cv2.rectangle(image, (595, 155), (740, 270), color_from_hsv(60), -1)
    cv2.rectangle(image, (570, 385), (735, 465), color_from_hsv(110), -1)
    for x, label in ((95, "RED H=2"), (365, "RED H=175"), (595, "GREEN")):
        cv2.putText(image, label, (x, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.putText(image, "BLUE", (620, 505), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.rectangle(image, (55, 385), (475, 455), (210, 210, 210), -1)
    for index, intensity in enumerate(range(20, 241, 20)):
        cv2.rectangle(image, (60 + index * 34, 390), (90 + index * 34, 450), (intensity, intensity, intensity), -1)
    cv2.putText(image, "BRIGHTNESS SCALE", (70, 495), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.circle(image, (260, 535), 3, color_from_hsv(2), -1)
    cv2.circle(image, (275, 535), 3, color_from_hsv(175), -1)
    cv2.putText(image, "x -> right, y -> down; 800 x 600", (35, 577), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 230, 230), 1, cv2.LINE_AA)
    return image


def make_noisy(image, seed):
    random = np.random.RandomState(seed)
    gaussian = random.normal(0, 16, image.shape)
    result = np.clip(image.astype(np.float32) + gaussian, 0, 255).astype(np.uint8)
    impulse = random.uniform(size=image.shape[:2])
    result[impulse < 0.008] = 0
    result[impulse > 0.992] = 255
    return result


def make_plane():
    document = np.full((300, 400, 3), 240, dtype=np.uint8)
    cv2.rectangle(document, (2, 2), (397, 297), (25, 25, 25), 4)
    cv2.putText(document, "PLANAR TARGET", (38, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.88, (35, 35, 35), 2, cv2.LINE_AA)
    for x in range(40, 380, 40):
        cv2.line(document, (x, 80), (x, 265), (170, 170, 170), 1)
    for y in range(85, 270, 30):
        cv2.line(document, (35, y), (365, y), (170, 170, 170), 1)
    cv2.arrowedLine(document, (75, 225), (300, 110), (180, 70, 15), 9, tipLength=0.18)
    for label, xy in (("1", (15, 28)), ("2", (365, 28)), ("3", (365, 282)), ("4", (15, 282))):
        cv2.putText(document, label, xy, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
    source = np.float32([[0, 0], [399, 0], [399, 299], [0, 299]])
    destination = np.array(PLANE_CORNERS, dtype=np.float32).reshape(4, 2) * np.float32([799, 599])
    transform = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(document, transform, (800, 600))
    mask = cv2.warpPerspective(np.full((300, 400), 255, np.uint8), transform, (800, 600))
    background = np.full((600, 800, 3), (85, 65, 40), dtype=np.uint8)
    background[mask > 0] = warped[mask > 0]
    return background


def write_demo_video(path, scene, frame_count, fps):
    height, width = scene.shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
    if not writer.isOpened():
        raise ValueError("Не удалось создать MJPG-видео. Повторите с --skip-video для изображений и проверьте Video I/O в OpenCV.")
    try:
        for index in range(frame_count):
            frame = scene.copy()
            progress = index / float(max(1, frame_count - 1))
            x = int(80 + 640 * progress)
            y = int(350 + 25 * math.sin(progress * 2 * math.pi))
            cv2.circle(frame, (x, y), 22, color_from_hsv(0), -1)
            cv2.putText(frame, "FRAME {:03d}".format(index), (600, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            writer.write(frame)
    finally:
        writer.release()
    capture = cv2.VideoCapture(str(path))
    try:
        ok, first = capture.read()
        if not ok or first is None or first.shape[:2] != scene.shape[:2]:
            raise ValueError("Созданное видео не читается этим OpenCV; используйте --skip-video и проверьте видеокодеки.")
    finally:
        capture.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Семя генератора шума, 0..2**32-1")
    parser.add_argument("--frames", type=int, default=60, help="Число видеокадров 2..300 (по умолчанию %(default)s)")
    parser.add_argument("--fps", type=float, default=15, help="Частота видео 1..60 (по умолчанию %(default)s)")
    parser.add_argument("--skip-video", action="store_true", help="Создать только изображения")
    args = parser.parse_args(argv)
    if not 0 <= args.seed < 2 ** 32 or not 2 <= args.frames <= 300 or not math.isfinite(args.fps) or not 1 <= args.fps <= 60:
        parser.error("Проверьте диапазоны --seed, --frames и --fps в --help.")
    output = ensure_out(COURSE_ROOT / "data")
    try:
        scene = make_scene()
        save_image(output / "scene.png", scene)
        save_image(output / "noisy.png", make_noisy(scene, args.seed))
        save_image(output / "portrait_plane.png", make_plane())
        if not args.skip_video:
            write_demo_video(output / "demo.avi", scene, args.frames, args.fps)
        save_json(output / "manifest.json", {
            "source": "Original synthetic course assets, no third-party photographs",
            "seed": args.seed, "image_wh": [800, 600], "large_red_objects_in_scene": 2,
            "small_red_specks": 2, "plane_corners_normalized": list(PLANE_CORNERS),
            "video_generated_this_run": not args.skip_video, "video_frames": args.frames if not args.skip_video else None,
            "video_fps": args.fps if not args.skip_video else None,
            "note": "portrait_plane.png is a flat geometric target, not a human portrait."
        })
    except (ValueError, OSError, cv2.error) as exc:
        parser.error(str(exc))
    print("Учебные данные созданы: {}".format(output))


if __name__ == "__main__":
    main()

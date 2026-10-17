"""Урок 03: рисование, HSV, бинаризация, морфология и границы."""

import argparse
import cv2
import numpy as np
from .common import ensure_out, image_arguments, read_image, red_mask, run_cli, save_image, save_json


def execute(args):
    if not 0 <= args.threshold <= 255:
        raise ValueError("--threshold должен быть от 0 до 255.")
    if args.kernel < 1 or args.kernel > 31 or args.kernel % 2 == 0:
        raise ValueError("--kernel должен быть нечётным числом от 1 до 31.")
    if not 0 <= args.canny[0] < args.canny[1] <= 255:
        raise ValueError("--canny LOW HIGH: требуется 0 <= LOW < HIGH <= 255.")
    image = read_image(args.input)
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = red_mask(image, args.s_min, args.v_min, args.hue_width)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (args.kernel, args.kernel))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    _, thresholded = cv2.threshold(gray, args.threshold, 255, cv2.THRESH_BINARY)
    canny = cv2.Canny(gray, args.canny[0], args.canny[1])
    annotated = image.copy()
    cv2.line(annotated, (0, height // 2), (width - 1, height // 2), (255, 255, 0), 2)
    cv2.rectangle(annotated, (width // 10, height // 10), (9 * width // 10, 9 * height // 10), (0, 255, 255), 2)
    cv2.circle(annotated, (width // 2, height // 2), max(1, min(width, height) // 12), (255, 255, 255), 2)
    cv2.ellipse(annotated, (3 * width // 4, 3 * height // 4), (max(1, width // 10), max(1, height // 18)), 20, 0, 360, (180, 0, 180), 2)
    triangle = np.int32([[width // 10, 3 * height // 4], [width // 5, 3 * height // 4], [3 * width // 20, 3 * height // 5]])
    cv2.polylines(annotated, [triangle], True, (255, 160, 0), 2)
    cv2.putText(annotated, "OpenCV: image coordinates", (12, max(18, height - 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    output = ensure_out(args.out)
    images = {"annotated": annotated, "hsv_h": hsv[:, :, 0], "hsv_s": hsv[:, :, 1], "hsv_v": hsv[:, :, 2],
              "red_mask": mask, "threshold": thresholded, "opened": opened, "closed": closed, "canny": canny}
    for name, result in images.items():
        save_image(output / (name + ".png"), result)
    report = {"threshold": args.threshold, "kernel": args.kernel, "canny": args.canny,
              "red_h_ranges": [[0, args.hue_width], [180 - args.hue_width, 179]],
              "s_min": args.s_min, "v_min": args.v_min,
              "red_pixels_before": int(cv2.countNonZero(mask)), "red_pixels_after": int(cv2.countNonZero(closed)),
              "threshold_white_pixels": int(cv2.countNonZero(thresholded)), "edge_pixels": int(cv2.countNonZero(canny))}
    save_json(output / "report.json", report)
    return report


def main(argv=None):
    parser = image_arguments(argparse.ArgumentParser(description=__doc__), 3)
    parser.add_argument("--threshold", type=int, default=120, help="Порог яркости 0..255 (по умолчанию %(default)s)")
    parser.add_argument("--kernel", type=int, default=3, help="Нечётный размер морфологического ядра 1..31")
    parser.add_argument("--s-min", type=int, default=80, help="Минимальная насыщенность красного 0..255")
    parser.add_argument("--v-min", type=int, default=60, help="Минимальная яркость красного 0..255")
    parser.add_argument("--hue-width", type=int, default=10, help="Ширина каждого диапазона красного, 1..30")
    parser.add_argument("--canny", type=int, nargs=2, default=[60, 160], metavar=("LOW", "HIGH"), help="Два порога Canny (по умолчанию %(default)s)")
    return run_cli(parser, execute, argv)


if __name__ == "__main__":
    main()

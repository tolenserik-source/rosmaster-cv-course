"""Урок 01: размеры, координаты, BGR, каналы и оттенки серого."""

import argparse
import cv2
from .common import image_arguments, read_image, run_cli, save_image, save_json, ensure_out


def process(image, x, y):
    height, width = image.shape[:2]
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("Пиксель ({}, {}) вне изображения {}x{}; допустимы x=0..{}, y=0..{}.".format(x, y, width, height, width - 1, height - 1))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    images = {"original": image.copy(), "grayscale": gray}
    for index, name in enumerate(("blue", "green", "red")):
        images["channel_" + name] = image[:, :, index].copy()
    report = {
        "width": width, "height": height, "channels": int(image.shape[2]),
        "dtype": str(image.dtype), "array_index_order": "image[y, x]",
        "pixel_xy": [x, y], "pixel_bgr": [int(v) for v in image[y, x]],
        "pixel_gray": int(gray[y, x]),
        "mean_bgr": [round(float(v), 3) for v in image.mean(axis=(0, 1))],
    }
    return images, report


def execute(args):
    image = read_image(args.input)
    height, width = image.shape[:2]
    x, y = args.pixel if args.pixel is not None else (width // 2, height // 2)
    images, report = process(image, x, y)
    output = ensure_out(args.out)
    for name, result in images.items():
        save_image(output / (name + ".png"), result)
    save_json(output / "report.json", report)
    print("Размер: {}x{}; пиксель ({}, {}), BGR={}".format(width, height, x, y, report["pixel_bgr"]))
    return report


def main(argv=None):
    parser = image_arguments(argparse.ArgumentParser(description=__doc__), 1)
    parser.add_argument("--pixel", type=int, nargs=2, metavar=("X", "Y"), help="Пиксель для измерения; по умолчанию центр кадра")
    return run_cli(parser, execute, argv)


if __name__ == "__main__":
    main()

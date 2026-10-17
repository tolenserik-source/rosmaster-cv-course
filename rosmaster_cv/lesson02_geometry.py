"""Урок 02: масштаб, вырезание, сдвиг, отражение и преобразования плоскости."""

import argparse
import math
import cv2
import numpy as np
from .common import ensure_out, image_arguments, read_image, run_cli, save_image, save_json


PLANE_CORNERS = (0.18, 0.16, 0.80, 0.22, 0.90, 0.86, 0.12, 0.78)


def execute(args):
    image = read_image(args.input)
    height, width = image.shape[:2]
    if min(height, width) < 2:
        raise ValueError("Для геометрических преобразований нужен кадр не меньше 2x2.")
    if not math.isfinite(args.scale) or not 0.01 <= args.scale <= 4:
        raise ValueError("--scale должен быть от 0.01 до 4.")
    if not math.isfinite(args.angle) or not all(math.isfinite(v) for v in args.translate):
        raise ValueError("Угол и сдвиг должны быть конечными числами.")
    x, y, crop_w, crop_h = args.crop if args.crop else (width // 4, height // 4, max(1, width // 2), max(1, height // 2))
    if min(x, y) < 0 or min(crop_w, crop_h) < 1 or x + crop_w > width or y + crop_h > height:
        raise ValueError("--crop X Y W H должен задавать непустую область внутри кадра {}x{}.".format(width, height))
    warp_w, warp_h = args.warp_size
    if not 2 <= warp_w <= 4096 or not 2 <= warp_h <= 4096:
        raise ValueError("--warp-size: обе стороны должны быть от 2 до 4096.")
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in args.src):
        raise ValueError("--src: восемь нормированных координат в диапазоне 0..1.")
    source = np.array(args.src, dtype=np.float32).reshape(4, 2)
    source *= np.array([width - 1, height - 1], dtype=np.float32)
    if not cv2.isContourConvex(source.reshape(-1, 1, 2)) or abs(cv2.contourArea(source)) < 1:
        raise ValueError("--src: четыре угла должны образовывать выпуклый четырёхугольник; порядок TL TR BR BL.")
    destination = np.float32([[0, 0], [warp_w - 1, 0], [warp_w - 1, warp_h - 1], [0, warp_h - 1]])
    perspective_matrix = cv2.getPerspectiveTransform(source, destination)
    dx, dy = args.translate
    translation = np.float32([[1, 0, dx], [0, 1, dy]])
    affine_matrix = np.float32([[1, 0.15, dx], [0, 1, dy]])
    rotation = cv2.getRotationMatrix2D(((width - 1) / 2.0, (height - 1) / 2.0), args.angle, 1.0)
    resized_size = (max(1, round(width * args.scale)), max(1, round(height * args.scale)))
    interpolation = cv2.INTER_AREA if args.scale < 1 else cv2.INTER_LINEAR
    marked = image.copy()
    cv2.polylines(marked, [np.rint(source).astype(np.int32)], True, (0, 200, 255), 3)
    for i, point in enumerate(source):
        cv2.putText(marked, str(i + 1), tuple(np.rint(point).astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    results = {
        "resized": cv2.resize(image, resized_size, interpolation=interpolation),
        "cropped": image[y:y + crop_h, x:x + crop_w].copy(),
        "translated": cv2.warpAffine(image, translation, (width, height)),
        "flipped": cv2.flip(image, args.flip),
        "rotated": cv2.warpAffine(image, rotation, (width, height)),
        "affine": cv2.warpAffine(image, affine_matrix, (width, height)),
        "perspective": cv2.warpPerspective(image, perspective_matrix, (warp_w, warp_h)),
        "source_corners": marked,
    }
    output = ensure_out(args.out)
    for name, result in results.items():
        save_image(output / (name + ".png"), result)
    report = {"input_wh": [width, height], "crop_xywh": [x, y, crop_w, crop_h], "scale": args.scale,
              "angle_degrees": args.angle, "translate_xy": args.translate, "flip_code": args.flip,
              "affine_matrix": affine_matrix.tolist(), "perspective_matrix": perspective_matrix.tolist(),
              "source_corners_px": source.tolist(),
              "result_wh": {name: [result.shape[1], result.shape[0]] for name, result in results.items()}}
    save_json(output / "report.json", report)
    return report


def main(argv=None):
    parser = image_arguments(argparse.ArgumentParser(description=__doc__), 2)
    parser.add_argument("--scale", type=float, default=0.5, help="Масштаб, 0.01..4 (по умолчанию %(default)s)")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "W", "H"), help="Вырезать область; по умолчанию центральная половина")
    parser.add_argument("--translate", type=float, nargs=2, default=[50, -25], metavar=("DX", "DY"), help="Сдвиг в пикселях (по умолчанию %(default)s)")
    parser.add_argument("--flip", type=int, choices=[-1, 0, 1], default=1, help="Отражение: 1 горизонтальное, 0 вертикальное, -1 оба")
    parser.add_argument("--angle", type=float, default=25, help="Угол поворота в градусах (по умолчанию %(default)s)")
    parser.add_argument("--src", type=float, nargs=8, default=list(PLANE_CORNERS), metavar="COORD", help="Углы плоскости TL TR BR BL, нормированные x y (восемь чисел)")
    parser.add_argument("--warp-size", type=int, nargs=2, default=[400, 300], metavar=("W", "H"), help="Размер выпрямленной плоскости (по умолчанию %(default)s)")
    return run_cli(parser, execute, argv)


if __name__ == "__main__":
    main()

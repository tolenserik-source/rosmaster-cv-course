"""Урок 04: шум, сглаживание, яркость, локальный контраст и восстановление."""

import argparse
import math
import cv2
import numpy as np
from .common import ensure_out, image_arguments, read_image, run_cli, save_image, save_json


def adjust_brightness(image, alpha=1.1, beta=20):
    """Линейная коррекция с насыщением; отрицательные значения не отражаются."""
    return np.clip(image.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)


def execute(args):
    if args.kernel < 3 or args.kernel > 31 or args.kernel % 2 == 0:
        raise ValueError("--kernel должен быть нечётным числом от 3 до 31.")
    if not math.isfinite(args.alpha) or not 0 <= args.alpha <= 4:
        raise ValueError("--alpha должен быть от 0 до 4.")
    if not math.isfinite(args.beta) or not -255 <= args.beta <= 255:
        raise ValueError("--beta должен быть от -255 до 255.")
    if not math.isfinite(args.clip_limit) or not 0 < args.clip_limit <= 40:
        raise ValueError("--clip-limit должен быть больше 0 и не больше 40.")
    if not 1 <= args.inpaint_radius <= 20:
        raise ValueError("--inpaint-radius должен быть от 1 до 20.")
    image = read_image(args.input)
    height, width = image.shape[:2]
    if min(height, width) < 16:
        raise ValueError("Для этого урока используйте изображение не меньше 16x16.")
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    light, channel_a, channel_b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=args.clip_limit, tileGridSize=(8, 8))
    local_contrast = cv2.cvtColor(cv2.merge((clahe.apply(light), channel_a, channel_b)), cv2.COLOR_LAB2BGR)
    if args.mask:
        mask = cv2.cvtColor(read_image(args.mask), cv2.COLOR_BGR2GRAY)
        if mask.shape != image.shape[:2]:
            raise ValueError("--mask должна иметь те же размеры, что и --input.")
        mask = np.where(mask > 0, 255, 0).astype(np.uint8)
        damaged = image.copy()
        mask_origin = "user-provided; white pixels mark missing data"
    else:
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.line(mask, (width // 3, height // 5), (width // 3, 4 * height // 5), 255, max(1, width // 120))
        damaged = image.copy()
        damaged[mask > 0] = (0, 0, 0)
        mask_origin = "synthetic scratch added to an input copy"
    if cv2.countNonZero(mask) == 0 or cv2.countNonZero(mask) == mask.size:
        raise ValueError("Маска должна отмечать часть повреждённого изображения, а не 0% или 100%.")
    images = {
        "noisy": image.copy(),
        "gaussian": cv2.GaussianBlur(image, (args.kernel, args.kernel), 0),
        "median": cv2.medianBlur(image, args.kernel),
        "bilateral": cv2.bilateralFilter(image, args.kernel, 60, 60),
        "clahe": local_contrast,
        "brightness": adjust_brightness(image, args.alpha, args.beta),
        "damaged": damaged,
        "damage_mask": mask,
        "inpainted": cv2.inpaint(damaged, mask, args.inpaint_radius, cv2.INPAINT_TELEA),
    }
    output = ensure_out(args.out)
    for name, result in images.items():
        save_image(output / (name + ".png"), result)
    order = ("noisy", "gaussian", "median", "bilateral", "clahe", "brightness")
    tile_w, tile_h = 400, 300
    tiles = []
    for name in order:
        tile = cv2.resize(images[name], (tile_w, tile_h), interpolation=cv2.INTER_AREA)
        cv2.rectangle(tile, (0, 0), (tile_w - 1, 29), (25, 25, 25), -1)
        cv2.putText(tile, name, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
        tiles.append(tile)
    save_image(output / "comparison.png", np.vstack((np.hstack(tiles[:3]), np.hstack(tiles[3:]))))
    report = {"kernel": args.kernel, "alpha": args.alpha, "beta": args.beta, "clip_limit": args.clip_limit,
              "mask_origin": mask_origin, "damaged_pixels": int(cv2.countNonZero(mask)),
              "inpaint_radius": args.inpaint_radius,
              "mean_gray": {name: round(float(cv2.cvtColor(images[name], cv2.COLOR_BGR2GRAY).mean()), 3) for name in order}}
    if args.reference:
        reference = read_image(args.reference)
        if reference.shape != image.shape:
            raise ValueError("--reference должна иметь те же размеры, что и --input.")
        report["mse_to_reference"] = {
            name: round(float(np.mean((images[name].astype(np.float64) - reference.astype(np.float64)) ** 2)), 3)
            for name in order
        }
    save_json(output / "report.json", report)
    return report


def main(argv=None):
    parser = image_arguments(argparse.ArgumentParser(description=__doc__), 4, "data/noisy.png")
    parser.add_argument("--kernel", type=int, default=5, help="Размер окна сглаживания, нечётный 3..31")
    parser.add_argument("--alpha", type=float, default=1.1, help="Множитель яркости 0..4")
    parser.add_argument("--beta", type=float, default=20, help="Прибавка к яркости, -255..255")
    parser.add_argument("--clip-limit", type=float, default=2.0, help="Ограничение локального контраста CLAHE, 0..40")
    parser.add_argument("--mask", help="Маска дефекта: белые пиксели нужно восстановить; без неё создаётся царапина")
    parser.add_argument("--inpaint-radius", type=int, default=3, help="Радиус восстановления, 1..20 пикселей")
    parser.add_argument("--reference", help="Чистое изображение для MSE; для синтетического noisy.png это data/scene.png")
    return run_cli(parser, execute, argv)


if __name__ == "__main__":
    main()

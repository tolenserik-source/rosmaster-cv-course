#!/usr/bin/env python3
"""Stationary visual inspection: red objects, per-frame measurements, no actuation."""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description="Итоговый проект: визуальный инспектор красных объектов")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="Один PNG/JPG")
    source_group.add_argument("--source", help="Локальное видео или подтверждённый индекс RGB-камеры")
    parser.add_argument("--max-frames", type=int, default=60)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--min-area", type=float, default=200.0)
    parser.add_argument("--saturation-min", type=int, default=80)
    parser.add_argument("--out", default="outputs/final")
    args = parser.parse_args()
    if not 1 <= args.max_frames <= 3000 or args.save_every < 1:
        parser.error("--max-frames: 1..3000; --save-every: положительное число")
    if args.min_area < 0 or not 0 <= args.saturation_min <= 255:
        parser.error("--min-area должен быть >= 0; --saturation-min: 0..255")
    try:
        import cv2
        from rosmaster_cv.common import read_image
        from rosmaster_cv.lesson05_applications import detect_red_objects
    except ImportError as exc:
        print("Не найдена библиотека: {}. Откройте docs/SETUP_ROBOT.md".format(exc), file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cap, rows = None, []
    total_started = time.perf_counter()
    try:
        still = read_image(args.input) if args.input else None
        if args.source is not None:
            if "://" in args.source:
                parser.error("Используйте локальное видео или локальную камеру")
            source = int(args.source) if args.source.isdigit() else args.source
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                raise RuntimeError("Источник не открылся: {}".format(args.source))
        for number in range(1, (1 if args.input else args.max_frames) + 1):
            if still is not None:
                frame = still
            else:
                ok, frame = cap.read()
                if not ok:
                    break
            started = time.perf_counter()
            mask, annotated, objects = detect_red_objects(frame, min_area=args.min_area, saturation_min=args.saturation_min)
            processing_ms = (time.perf_counter() - started) * 1000.0
            rows.append({"frame": number, "objects": len(objects),
                         "mask_pixels": int(cv2.countNonZero(mask)), "processing_ms": processing_ms})
            if number == 1 or number % args.save_every == 0:
                for name, image in (("annotated", annotated), ("mask", mask)):
                    target = out / "{}_{:04d}.png".format(name, number)
                    if not cv2.imwrite(str(target), image):
                        raise RuntimeError("Не удалось сохранить {}".format(target))
        if not rows:
            raise RuntimeError("Ни одного кадра не получено")
        with (out / "measurements.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["frame", "objects", "mask_pixels", "processing_ms"])
            writer.writeheader()
            writer.writerows(rows)
        elapsed = time.perf_counter() - total_started
        summary = {
            "input": args.input or args.source, "frames": len(rows),
            "frames_with_detection": sum(row["objects"] > 0 for row in rows),
            "mean_processing_ms": sum(row["processing_ms"] for row in rows) / len(rows),
            "pipeline_frames_per_second": len(rows) / elapsed if elapsed else None,
            "min_area": args.min_area, "saturation_min": args.saturation_min,
            "note": "Counts are not accuracy. Compare with manually labelled frames. Runtime is not a robot specification."
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Обработано {} кадров; результаты: {}".format(len(rows), out))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("Ошибка: {}".format(exc), file=sys.stderr)
        return 2
    finally:
        if cap is not None:
            cap.release()


if __name__ == "__main__":
    sys.exit(main())

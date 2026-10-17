#!/usr/bin/env python3
"""Save a finite set of frames from an explicitly selected source; no GUI."""
import argparse
import json
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Сохранить кадры выбранной RGB-камеры или видео")
    parser.add_argument("--source", required=True, help="Подтверждённый индекс камеры, путь устройства или видеофайл")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--out", default="outputs/capture")
    args = parser.parse_args()
    if not 1 <= args.frames <= 3000 or args.save_every < 1:
        parser.error("--frames: 1..3000, --save-every: положительное число")
    try:
        import cv2
    except ImportError:
        print("OpenCV не найден. Выполните tools/doctor.py и прочитайте docs/SETUP_ROBOT.md", file=sys.stderr)
        return 2
    source = int(args.source) if args.source.isdigit() else args.source
    if isinstance(source, str) and "://" in source:
        parser.error("В этом практикуме используйте локальный файл или локальное устройство камеры")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(source)
    count, saved = 0, []
    started = time.perf_counter()
    try:
        if not cap.isOpened():
            raise RuntimeError("Источник не открылся: проверьте путь, устройство и занятость камеры")
        source_fps = float(cap.get(cv2.CAP_PROP_FPS))
        while count < args.frames:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
            if count == 1 or count % args.save_every == 0:
                target = out / "frame_{:04d}.png".format(count)
                if not cv2.imwrite(str(target), frame):
                    raise RuntimeError("Не удалось записать {}".format(target))
                saved.append(target.name)
        if not count:
            raise RuntimeError("Источник открыт, но ни одного кадра не получено")
        elapsed = time.perf_counter() - started
        report = {"source": args.source, "frames_read": count, "frames_requested": args.frames,
                  "files": saved, "source_reported_fps": source_fps,
                  "elapsed_seconds": elapsed, "measured_read_fps": count / elapsed if elapsed else None,
                  "note": "measured_read_fps includes reading and saving; it is not a camera specification"}
        (out / "capture.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Прочитано кадров: {}; сохранено: {}; папка: {}".format(count, len(saved), out))
        return 0
    except (RuntimeError, OSError) as exc:
        print("Ошибка: {}".format(exc), file=sys.stderr)
        return 2
    finally:
        cap.release()


if __name__ == "__main__":
    sys.exit(main())

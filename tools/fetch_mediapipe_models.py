#!/usr/bin/env python3
"""Explicit optional download of official Google Landmarker Tasks models."""
import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELS = {
    "hands": ("hand_landmarker.task", "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"),
    "pose": ("pose_landmarker_lite.task", "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"),
    "face": ("face_landmarker.task", "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task")
}


def download(mode, destination, force=False):
    filename, url = MODELS[mode]
    target = destination / filename
    if target.exists() and not force:
        print("Уже существует: {} (для замены используйте --force)".format(target))
        return
    temporary = target.with_suffix(target.suffix + ".part")
    digest, size = hashlib.sha256(), 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "rosmaster-cv-course/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as stream:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > 40 * 1024 * 1024:
                    raise RuntimeError("Неожиданно большой ответ; загрузка прекращена")
                digest.update(block)
                stream.write(block)
        if size < 10000:
            raise RuntimeError("Ответ слишком мал для модели; файл не принят")
        temporary.replace(target)
        metadata = {"source": url, "bytes": size, "sha256": digest.hexdigest(),
                    "note": "SHA256 records downloaded bytes; it is not an independent upstream signature"}
        target.with_suffix(target.suffix + ".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        print("Сохранено {} ({} байт)".format(target, size))
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description="Загрузить официальные модели MediaPipe по явному запросу")
    parser.add_argument("--mode", choices=("hands", "pose", "face", "all"), default="all")
    parser.add_argument("--destination", default="models")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    destination = Path(args.destination)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for mode in (MODELS if args.mode == "all" else [args.mode]):
            download(mode, destination, args.force)
        return 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print("Ошибка загрузки: {}. Проверьте сеть и официальный URL в docs/SOURCES.md".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Создать обычный учебный QR-код строго в data/qr.png этого курса."""

import argparse
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rosmaster_cv.common import save_image


def make_qr(text, scale=10):
    if not text or len(text.encode("utf-8")) > 256:
        raise ValueError("Текст QR должен содержать от 1 до 256 байт UTF-8.")
    if not 2 <= scale <= 30:
        raise ValueError("--scale должен быть от 2 до 30.")
    if hasattr(cv2, "QRCodeEncoder_create"):
        modules = cv2.QRCodeEncoder_create().encode(text)
        # Дополнительное белое поле сохраняет quiet zone даже между реализациями.
        modules = cv2.copyMakeBorder(modules, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    else:
        try:
            import qrcode
        except ImportError:
            raise ValueError("Этот OpenCV не содержит QRCodeEncoder. Используйте готовый data/qr.png или установите qrcode в отдельную учебную среду.")
        code = qrcode.QRCode(border=4, box_size=1)
        code.add_data(text)
        code.make(fit=True)
        modules = np.where(np.asarray(code.get_matrix(), dtype=bool), 0, 255).astype(np.uint8)
    return cv2.resize(modules, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="KAZNU-ROSMASTER-9.5", help="Содержимое QR (по умолчанию %(default)s)")
    parser.add_argument("--scale", type=int, default=10, help="Пикселей на модуль, 2..30")
    args = parser.parse_args(argv)
    try:
        image = make_qr(args.text, args.scale)
        output = ROOT / "data/qr.png"
        save_image(output, image)
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
        if decoded != args.text:
            raise ValueError("QR сохранён, но проверочное декодирование не совпало. Увеличьте --scale или сократите текст.")
    except (ValueError, OSError, cv2.error) as exc:
        parser.error(str(exc))
    print("Создан и проверен QR: {} | {}".format(output, args.text))


if __name__ == "__main__":
    main()

"""Общие операции с изображениями; совместимо с Python 3.6 и OpenCV 4.x."""

import json
from pathlib import Path
import cv2
import numpy as np


def ensure_out(path):
    """Создать каталог результатов и вернуть pathlib.Path."""
    directory = Path(path).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise ValueError("Путь результатов не является каталогом: {}".format(directory))
    return directory


def read_image(path):
    """Прочитать изображение как uint8 BGR, с понятной ошибкой и Unicode-путями."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(
            "Не найдено изображение: {}. Проверьте --input и рабочую папку; "
            "учебные данные создаёт python3 tools/generate_data.py.".format(source)
        )
    encoded = np.fromfile(str(source), dtype=np.uint8)
    if encoded.size == 0:
        raise ValueError("Файл изображения пуст: {}".format(source))
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ValueError("OpenCV не смог прочитать изображение: {}".format(source))
    return image


def save_image(path, image):
    """Сохранить изображение; ошибка записи никогда не игнорируется."""
    target = Path(path).expanduser()
    if image is None or image.size == 0:
        raise ValueError("Нельзя сохранить пустое изображение: {}".format(target))
    if not target.suffix:
        raise ValueError("Укажите расширение изображения, например .png: {}".format(target))
    ensure_out(target.parent)
    ok, encoded = cv2.imencode(target.suffix, image)
    if not ok:
        raise OSError("OpenCV не смог закодировать изображение: {}".format(target))
    encoded.tofile(str(target))
    return target


def save_json(path, data):
    target = Path(path).expanduser()
    ensure_out(target.parent)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    return target


def red_mask(image, saturation_min=80, value_min=60, hue_width=10):
    """Маска красного: объединение диапазонов около H=0 и H=179.

    В 8-битном HSV OpenCV H лежит в 0..179, S и V — в 0..255.
    """
    if not 0 <= saturation_min <= 255 or not 0 <= value_min <= 255:
        raise ValueError("Пороги S и V должны лежать в диапазоне 0..255.")
    if not 1 <= hue_width <= 30:
        raise ValueError("Ширина красного диапазона H должна быть от 1 до 30.")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    low = cv2.inRange(hsv, (0, saturation_min, value_min), (hue_width, 255, 255))
    high = cv2.inRange(hsv, (180 - hue_width, saturation_min, value_min), (179, 255, 255))
    return cv2.bitwise_or(low, high)


def find_external_contours(mask):
    """Вернуть внешние контуры независимо от длины ответа findContours."""
    result = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return result[-2]


def image_arguments(parser, lesson, default_input="data/scene.png"):
    parser.add_argument("--input", default=default_input, help="Входное изображение (по умолчанию %(default)s)")
    parser.add_argument("--out", default="outputs/{:02d}".format(lesson), help="Каталог результатов (по умолчанию %(default)s)")
    return parser


def run_cli(parser, action, argv=None):
    """Обработка ожидаемых ошибок без длинной трассировки для студента."""
    args = parser.parse_args(argv)
    try:
        result = action(args)
    except (OSError, ValueError, cv2.error) as exc:
        parser.error(str(exc))
    print("Готово: {}".format(Path(args.out).expanduser().resolve()))
    return result

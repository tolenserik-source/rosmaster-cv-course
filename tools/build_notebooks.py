#!/usr/bin/env python3
"""Build the eleven student notebooks using only the Python standard library."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit, urlunsplit


LESSONS = [
    ("01_intro", "Чтение изображения и первый результат"),
    ("02_geometry", "Геометрические преобразования"),
    ("03_drawing", "Маски, контуры и рисование"),
    ("04_enhancement", "Улучшение изображения"),
    ("05_applications", "QR-коды и готовые модели"),
    ("06_ar", "Калибровка и дополненная реальность"),
    ("07_markers", "Геометрия маркера и ALVAR"),
    ("08_ros_image", "Изображения в ROS"),
    ("09_ros_processing", "Обработка потока ROS"),
    ("10_data", "LaserScan и облака точек"),
    ("11_mediapipe", "Ориентиры MediaPipe"),
]

BOOTSTRAP = '''from pathlib import Path
import subprocess
import sys

# Jupyter may start in the repository root or in its notebooks directory.
ROOT = None
for candidate in (Path.cwd().resolve(), Path.cwd().resolve().parent):
    if (candidate / "rosmaster_cv").is_dir() and (candidate / "lessons").is_dir():
        ROOT = candidate
        break
if ROOT is None:
    raise RuntimeError("Откройте ноутбук из корня репозитория или его папки notebooks.")

def run_module(module, *arguments):
    command = [sys.executable, "-m", "rosmaster_cv." + module]
    command.extend(str(argument) for argument in arguments)
    return subprocess.run(command, cwd=str(ROOT), check=True)

def run_tool(filename, *arguments):
    command = [sys.executable, str(ROOT / "tools" / filename)]
    command.extend(str(argument) for argument in arguments)
    return subprocess.run(command, cwd=str(ROOT), check=True)

print("Корень курса:", ROOT)
print("Python ядра:", sys.executable)
'''

PREVIEW = '''def show_results(relative_directory, limit=4):
    directory = ROOT / relative_directory
    paths = sorted(directory.glob("*.png"))[:limit]
    if not paths:
        print("Изображений пока нет:", directory)
        return
    try:
        from IPython.display import Image, display
    except ImportError:
        for path in paths:
            print(path)
        return
    for path in paths:
        print(path.relative_to(ROOT))
        display(Image(filename=str(path)))
'''


def rebase_markdown(text, source_path, output_dir):
    """Keep chapter-local Markdown links usable from the notebooks directory."""
    def change(match):
        target = match.group(2)
        wrapped = target.startswith("<") and target.endswith(">")
        raw = target[1:-1] if wrapped else target
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc or not parts.path or raw.startswith("/"):
            return match.group(0)
        absolute = (source_path.parent / parts.path).resolve()
        relative = os.path.relpath(str(absolute), str(output_dir)).replace(os.sep, "/")
        rebased = urlunsplit(("", "", relative, parts.query, parts.fragment))
        if wrapped:
            rebased = "<" + rebased + ">"
        return match.group(1) + rebased + match.group(3)

    # Inline images and links; titles, if any, are left intact.
    text = re.sub(r"(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^\s)]+)([^\n]*?\))", change, text)

    def change_reference(match):
        # Reuse the same URL logic with explicit groups instead of altering labels.
        prefix, target, suffix = match.group(1), match.group(2), match.group(3)
        wrapped = target.startswith("<") and target.endswith(">")
        raw = target[1:-1] if wrapped else target
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc or not parts.path or raw.startswith("/"):
            return match.group(0)
        absolute = (source_path.parent / parts.path).resolve()
        relative = os.path.relpath(str(absolute), str(output_dir)).replace(os.sep, "/")
        rebased = urlunsplit(("", "", relative, parts.query, parts.fragment))
        return prefix + ("<" + rebased + ">" if wrapped else rebased) + suffix

    return re.sub(r"^(\s*\[[^\]\n]+\]:\s*)(<[^>\n]+>|\S+)(.*)$", change_reference, text, flags=re.M)


def markdown_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code_cell(source, tags=None):
    compile(source, "<notebook cell>", "exec")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": tags or []},
        "outputs": [],
        "source": source.splitlines(True),
    }


def check_chapter_links(chapter):
    text = chapter.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s)]+)", text)
    targets.extend(re.findall(r"^\s*\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", text, flags=re.M))
    missing = []
    for target in targets:
        target = target[1:-1] if target.startswith("<") and target.endswith(">") else target
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        if not (chapter.parent / unquote(parts.path)).exists():
            missing.append(target)
    return missing


def practice_cells(number):
    if number == 1:
        return [
            markdown_cell("На общем ROSMASTER задайте своё имя папки в `STUDENT`. Ядро Jupyter должно работать на роботе: локальное ядро запускает код на ноутбуке. SSH и PowerShell из главы выполняются в терминалах. Учебные данные уже входят в курс.\n"),
            code_cell('STUDENT = "ivanov"  # Замените на свою фамилию латиницей или номер команды.\nif not STUDENT or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in STUDENT):\n    raise ValueError("STUDENT: используйте строчные латинские буквы, цифры, _ или -.")\nOUT = "outputs/" + STUDENT + "/01"\n', ["parameters"]),
            code_cell('run_module("lesson01_intro", "--input", "data/scene.png", "--out", OUT + "/baseline")\nrun_module("lesson01_intro", "--input", "data/scene.png", "--pixel", "160", "200", "--out", OUT + "/red")\nrun_module("lesson01_intro", "--input", "data/scene.png", "--pixel", "650", "420", "--out", OUT + "/blue")\n'),
            code_cell(PREVIEW + '\nshow_results(OUT + "/baseline", limit=5)\nprint((ROOT / OUT / "red" / "report.json").read_text(encoding="utf-8"))\n'),
        ]
    if number <= 5:
        stem = LESSONS[number - 1][0]
        input_name = "noisy.png" if number == 4 else "scene.png"
        code = 'run_tool("generate_data.py")\n'
        code += 'run_module("lesson%s", "--input", "data/%s", "--out", "outputs/%02d")\n' % (stem, input_name, number)
        return [code_cell(code), code_cell(PREVIEW + '\nshow_results("outputs/%02d")\n' % number)]
    if number == 6:
        return [
            code_cell('run_module("lesson06_ar", "--synthetic")\n'),
            code_cell(PREVIEW + '\nshow_results("outputs/06")\n'),
            markdown_cell("Синтетический пример проверяет последовательность операций. Для измерений на камере выполните реальную калибровку из главы; размеры и матрицу камеры берите из своих данных.\n"),
        ]
    if number == 7:
        return [
            code_cell('run_module("lesson07_markers", "--diagnose")\n'),
            markdown_cell("Следующая ячейка показывает преобразование по **четырём явно заданным углам**. Она не обнаруживает ALVAR или ArUco и не выдаёт эти углы за результат детектора. ALVAR запускается отдельно по инструкции главы.\n"),
            code_cell('run_module("lesson06_ar", "--synthetic")\nrun_module("lesson07_markers", "--input", "outputs/06/checkerboard.png",\n           "--corners", "100", "100", "500", "100", "500", "350", "100", "350")\n'),
            code_cell(PREVIEW + '\nshow_results("outputs/07")\n'),
        ]
    if number == 8:
        return [
            code_cell('RUN_ON_ROBOT = False\nIMAGE_TOPIC = ""  # Впишите существующий топик sensor_msgs/Image из rostopic list.\nIMAGE_ENCODING = "bgr8"  # Для исходной глубины используйте passthrough.\n', ["parameters"]),
            code_cell('if RUN_ON_ROBOT:\n    if not IMAGE_TOPIC or not IMAGE_TOPIC.startswith("/"):\n        raise ValueError("Сначала укажите реальный IMAGE_TOPIC и прочитайте главу о кодировках.")\n    run_module("lesson08_ros_image", "--topic", IMAGE_TOPIC,\n               "--encoding", IMAGE_ENCODING, "--output", "outputs/08/frame.png", "--timeout", "10")\nelse:\n    print("ROS-захват выключен. Прочитайте главу, укажите IMAGE_TOPIC и затем включите RUN_ON_ROBOT.")\n'),
        ]
    if number == 9:
        return [
            code_cell('RUN_ON_ROBOT = False\nIMAGE_TOPIC = ""  # Впишите существующий топик цветного sensor_msgs/Image.\nOUTPUT_TOPIC = "/course/red_mask"  # Топик результата этого упражнения.\n', ["parameters"]),
            code_cell('if RUN_ON_ROBOT:\n    if not IMAGE_TOPIC or not IMAGE_TOPIC.startswith("/"):\n        raise ValueError("Сначала укажите реальный IMAGE_TOPIC.")\n    run_module("lesson09_ros_processing", "--topic", IMAGE_TOPIC,\n               "--seconds", "30", "--output-topic", OUTPUT_TOPIC)\nelse:\n    print("ROS-обработка выключена. Настройте IMAGE_TOPIC по инструкции главы перед включением.")\n'),
        ]
    if number == 10:
        return [
            code_cell('run_module("lesson10_data", "--synthetic")\n'),
            code_cell('run_module("lesson10_data", "--pcd", "outputs/10/synthetic_cloud.pcd",\n           "--pcd-units", "m", "--output-dir", "outputs/10/cloud")\nrun_module("lesson10_data", "--input-json", "outputs/10/synthetic_scan.json",\n           "--transform-json", "outputs/10/synthetic_rotation.json",\n           "--output-dir", "outputs/10/rotated")\n'),
            code_cell(PREVIEW + '\nshow_results("outputs/10")\nshow_results("outputs/10/cloud")\nshow_results("outputs/10/rotated")\n'),
        ]
    if number == 11:
        return [
            code_cell('RUN_ON_ROBOT = False\nINPUT_IMAGE = ""  # Путь к вашему изображению; камера не открывается автоматически.\nMODEL_FILE = ""  # Путь к скачанной .task-модели, соответствующей MODE.\nMODE = "hands"  # hands, pose или face; выберите совместимую модель по главе.\n', ["parameters"]),
            code_cell('if RUN_ON_ROBOT:\n    if not INPUT_IMAGE or not MODEL_FILE:\n        raise ValueError("Сначала укажите INPUT_IMAGE и MODEL_FILE по инструкции главы.")\n    image_path = ROOT / INPUT_IMAGE\n    model_path = ROOT / MODEL_FILE\n    if not image_path.is_file() or not model_path.is_file():\n        raise FileNotFoundError("Изображение или модель не найдены. Проверьте указанные пути.")\n    run_module("lesson11_mediapipe", "--input", image_path, "--mode", MODE,\n               "--backend", "tasks", "--model", model_path)\nelse:\n    print("MediaPipe выключен. Сначала подготовьте совместимое окружение, изображение и модель.")\n'),
        ]
    raise ValueError("Unknown lesson: %s" % number)


def make_notebook(number, stem, title, chapter, output_dir):
    source = chapter.read_text(encoding="utf-8")
    if not source.strip():
        raise ValueError("Пустая глава: %s" % chapter)
    chapter_text = rebase_markdown(source, chapter, output_dir)
    guarded = number in (8, 9, 11)
    introduction = "# Практикум %02d · %s\n\n" % (number, title)
    introduction += "Ниже находится полная глава курса, затем — ячейки практики. Прочитайте главу перед изменением параметров.\n\n"
    if guarded:
        introduction += "При **Run All** выполнение аппаратной части пропускается: `RUN_ON_ROBOT = False`. Включайте её после настройки окружения и собственных входных данных.\n"
    else:
        introduction += "Стандартный **Run All** использует учебные изображения или синтетические данные. Подготовьте Python с OpenCV и NumPy по стартовой инструкции.\n"
    cells = [
        markdown_cell(introduction),
        markdown_cell(chapter_text),
        markdown_cell("---\n\n## Ячейки практики\n\nЗапускайте последовательно. Команды используют тот же Python, что и ядро ноутбука. Рабочая папка дочерних процессов — корень репозитория. Ошибка команды останавливает ячейку и показывает причину.\n"),
        code_cell(BOOTSTRAP),
    ]
    cells.extend(practice_cells(number))
    cells.append(markdown_cell("## Результат самостоятельной работы\n\nВыполните задания и критерии приёмки из главы. Сохраните созданные изображения и JSON, параметры запуска и краткие ответы в своём отчёте. Повторите опыт с собственными данными после успешного учебного запуска.\n"))
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "file_extension": ".py", "mimetype": "text/x-python", "pygments_lexer": "ipython3"},
            "rosmaster_course": {"lesson": number, "source": "lessons/" + stem + ".md", "hardware_enabled_by_default": False},
        },
        "nbformat": 4,
        "nbformat_minor": 2,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Also require every local link in a source chapter to exist.")
    parser.add_argument("--check", action="store_true", help="Check that committed notebooks match the current chapters; do not write.")
    arguments = parser.parse_args(argv)
    root = arguments.repo_root.resolve()
    output_dir = arguments.output_dir or root / "notebooks"
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir = output_dir.resolve()
    missing = []
    for stem, _ in LESSONS:
        for path in (root / "lessons" / (stem + ".md"), root / "rosmaster_cv" / ("lesson" + stem + ".py")):
            if not path.is_file():
                missing.append(str(path.relative_to(root)))
    if not (root / "tools" / "generate_data.py").is_file():
        missing.append("tools/generate_data.py")
    if missing:
        parser.error("Сначала восстановите исходники: " + ", ".join(missing))
    if arguments.strict:
        broken_links = []
        for stem, _ in LESSONS:
            chapter = root / "lessons" / (stem + ".md")
            broken_links.extend(chapter.name + ": " + target for target in check_chapter_links(chapter))
        if broken_links:
            parser.error("Не найдены локальные ссылки в главах: " + "; ".join(broken_links))
    generated = []
    for number, (stem, title) in enumerate(LESSONS, 1):
        notebook = make_notebook(number, stem, title, root / "lessons" / (stem + ".md"), output_dir)
        serialized = json.dumps(notebook, ensure_ascii=False, indent=2) + "\n"
        generated.append((output_dir / (stem + ".ipynb"), serialized))
    stale = []
    if not arguments.check:
        output_dir.mkdir(parents=True, exist_ok=True)
    for target, serialized in generated:
        if arguments.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != serialized:
                stale.append(target.name)
        else:
            target.write_text(serialized, encoding="utf-8")
    if stale:
        print("Ноутбуки требуют пересборки: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(("Проверено" if arguments.check else "Создано") + " ноутбуков: %d" % len(generated))
    return 0


if __name__ == "__main__":
    sys.exit(main())

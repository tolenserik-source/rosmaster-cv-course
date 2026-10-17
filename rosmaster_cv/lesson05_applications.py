"""Урок 05: объекты по цвету, QR и дополнительные детекторы OpenCV DNN/Haar."""

import argparse
import math
from pathlib import Path
import cv2
import numpy as np
from .common import (ensure_out, find_external_contours, image_arguments, read_image,
                     red_mask, run_cli, save_image, save_json)


def detect_red_objects(image, min_area=200.0, saturation_min=80, value_min=60, kernel=3):
    """Вернуть (маска, подписанный кадр, список внешних красных объектов)."""
    if not math.isfinite(min_area) or min_area < 0:
        raise ValueError("Минимальная площадь должна быть конечным неотрицательным числом.")
    if kernel < 1 or kernel > 31 or kernel % 2 == 0:
        raise ValueError("Размер ядра должен быть нечётным числом от 1 до 31.")
    mask = red_mask(image, saturation_min, value_min)
    element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, element)
    annotated = image.copy()
    objects = []
    for contour in find_external_contours(mask):
        area = float(cv2.contourArea(contour))
        moments = cv2.moments(contour)
        if area < min_area or moments["m00"] <= 0:
            continue
        center = [moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]]
        objects.append({"area_px2": round(area, 3), "center_px": [round(v, 3) for v in center],
                        "bbox_xywh": [int(v) for v in cv2.boundingRect(contour)]})
    objects.sort(key=lambda obj: (obj["center_px"][0], obj["center_px"][1]))
    for index, obj in enumerate(objects, 1):
        obj["id_in_frame"] = index
        x, y, width, height = obj["bbox_xywh"]
        center = tuple(int(round(v)) for v in obj["center_px"])
        cv2.rectangle(annotated, (x, y), (x + width - 1, y + height - 1), (0, 255, 0), 2)
        cv2.circle(annotated, center, 5, (255, 255, 255), -1)
        cv2.putText(annotated, "red {}: {:.0f} px2".format(index, obj["area_px2"]), (x, max(16, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return mask, annotated, objects


def decode_qr(image):
    detector = cv2.QRCodeDetector()
    text, points, _ = detector.detectAndDecode(image)
    annotated = image.copy()
    corners = []
    if points is not None:
        corners = np.asarray(points).reshape(-1, 2).tolist()
        cv2.polylines(annotated, [np.rint(points).astype(np.int32).reshape(-1, 1, 2)], True, (0, 200, 0), 3)
    return annotated, {"decoded": bool(text), "text": text, "corners_px": corners,
                       "note": "QR content is recorded as data; it is never executed or opened."}


def require_file(path, description):
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError("Не найден {}: {}. Укажите существующий файл; модели не входят в учебный комплект.".format(description, source))
    return str(source)


def detect_faces(image, cascade_path=None):
    if cascade_path:
        filename = require_file(cascade_path, "Haar-каскад")
    else:
        candidates = []
        if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            candidates.append(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        for directory in ("/usr/share/opencv4/haarcascades", "/usr/share/opencv/haarcascades"):
            candidates.append(Path(directory) / "haarcascade_frontalface_default.xml")
        filename = next((str(p) for p in candidates if p.is_file()), None)
        if filename is None:
            raise ValueError("Haar-каскад не найден. Передайте --cascade /путь/haarcascade_frontalface_default.xml.")
    detector = cv2.CascadeClassifier(filename)
    if detector.empty():
        raise ValueError("Не удалось прочитать Haar-каскад: {}".format(filename))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    boxes = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    annotated = image.copy()
    faces = []
    for box in boxes:
        x, y, width, height = [int(v) for v in box]
        faces.append({"bbox_xywh": [x, y, width, height]})
        cv2.rectangle(annotated, (x, y), (x + width, y + height), (255, 160, 0), 2)
    return annotated, {"task": "face detection, not identity recognition", "faces": faces}


def detect_ssd(image, model_path, config_path, labels_path, threshold):
    """TensorFlow MobileNet v2 COCO; подготовка входа следует примеру Yahboom 9.5."""
    model = require_file(model_path, "SSD model .pb")
    config = require_file(config_path, "SSD text graph .txt/.pbtxt")
    labels = []
    if labels_path:
        with open(require_file(labels_path, "SSD labels"), encoding="utf-8") as handle:
            labels = [line.strip() for line in handle.read().splitlines()]
    net = cv2.dnn.readNetFromTensorflow(model, config)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    blob = cv2.dnn.blobFromImage(image, scalefactor=1.0, size=(300, 300), mean=(104, 117, 123), swapRB=True, crop=False)
    net.setInput(blob)
    raw = net.forward()
    if raw.ndim != 4 or raw.shape[0:2] != (1, 1) or raw.shape[-1] != 7:
        raise ValueError("SSD-выход {} несовместим с ожидаемым [1,1,N,7]. Проверьте пару model/config.".format(raw.shape))
    height, width = image.shape[:2]
    annotated = image.copy()
    detections = []
    for row in raw[0, 0]:
        if not np.isfinite(row).all() or float(row[2]) < threshold:
            continue
        class_id = int(row[1])
        x1, y1, x2, y2 = np.rint(row[3:7] * np.array([width, height, width, height])).astype(int)
        x1, x2 = int(np.clip(x1, 0, width - 1)), int(np.clip(x2, 0, width - 1))
        y1, y2 = int(np.clip(y1, 0, height - 1)), int(np.clip(y2, 0, height - 1))
        if class_id < 1 or x2 <= x1 or y2 <= y1:
            continue
        label = labels[class_id - 1] if 0 < class_id <= len(labels) and labels[class_id - 1] else "class_{}".format(class_id)
        score = float(row[2])
        detections.append({"class_id": class_id, "label": label, "confidence": round(score, 5),
                           "bbox_xyxy": [x1, y1, x2, y2]})
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 255), 2)
        cv2.putText(annotated, "{} {:.2f}".format(label, score), (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 2)
    return annotated, {"framework": "TensorFlow", "threshold": threshold, "detections": detections,
                       "preprocessing": {"size": [300, 300], "scale": 1.0, "mean": [104, 117, 123], "swapRB": True},
                       "label_rule": "line index = class_id - 1; keep COCO ID placeholders"}


def detect_pose(image, prototxt_path, model_path, pose_format, threshold):
    """Учебный single-person разбор COCO18/MPI15 heatmaps; без multi-person PAF."""
    config = require_file(prototxt_path, "Pose prototxt")
    model = require_file(model_path, "Pose .caffemodel")
    count = 18 if pose_format == "coco" else 15
    pairs = ([(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
             if pose_format == "coco" else [(0, 1), (1, 2), (2, 3), (3, 4), (1, 5), (5, 6), (6, 7), (1, 14), (14, 8), (8, 9), (9, 10), (14, 11), (11, 12), (12, 13)])
    net = cv2.dnn.readNetFromCaffe(config, model)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    net.setInput(cv2.dnn.blobFromImage(image, 1.0 / 255, (368, 368), (0, 0, 0), swapRB=False, crop=False))
    raw = net.forward()
    if raw.ndim != 4 or raw.shape[0] != 1 or raw.shape[1] < count:
        raise ValueError("Выход Pose {} не содержит {} карт точек. Проверьте --pose-format и модель.".format(raw.shape, count))
    height, width = image.shape[:2]
    annotated = image.copy()
    keypoints = []
    points = []
    for index in range(count):
        heatmap = raw[0, index]
        _, confidence, _, location = cv2.minMaxLoc(heatmap)
        point = (int(width * location[0] / heatmap.shape[1]), int(height * location[1] / heatmap.shape[0])) if confidence >= threshold else None
        points.append(point)
        keypoints.append({"index": index, "xy": list(point) if point is not None else None, "confidence": round(float(confidence), 5)})
        if point is not None:
            cv2.circle(annotated, point, 4, (0, 255, 255), -1)
            cv2.putText(annotated, str(index), point, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    for start, end in pairs:
        if points[start] is not None and points[end] is not None:
            cv2.line(annotated, points[start], points[end], (0, 200, 0), 2)
    return annotated, {"format": pose_format, "threshold": threshold, "keypoints": keypoints,
                       "limitation": "Single-person heatmap maxima only; no PAF association or multi-person separation."}


def execute(args):
    for value, name in ((args.confidence, "--confidence"), (args.pose_threshold, "--pose-threshold")):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("{} должен быть от 0 до 1.".format(name))
    if bool(args.ssd_model) != bool(args.ssd_config):
        raise ValueError("Передайте вместе --ssd-model и --ssd-config.")
    if args.ssd_labels and not args.ssd_model:
        raise ValueError("--ssd-labels используется вместе с --ssd-model и --ssd-config.")
    if bool(args.pose_model) != bool(args.pose_prototxt):
        raise ValueError("Передайте вместе --pose-model и --pose-prototxt.")
    if args.cascade and not args.faces:
        raise ValueError("--cascade используется вместе с --faces.")
    image = read_image(args.input)
    mask, annotated, objects = detect_red_objects(image, args.min_area, args.s_min, args.v_min, args.kernel)
    output = ensure_out(args.out)
    save_image(output / "red_mask.png", mask)
    save_image(output / "objects.png", annotated)
    object_report = {"input": args.input, "count": len(objects), "min_area_px2": args.min_area, "objects": objects,
                     "note": "IDs are local to this frame; centers are image pixels, not robot/world coordinates."}
    save_json(output / "objects.json", object_report)
    report = {"color_object_count": len(objects), "input_wh": [image.shape[1], image.shape[0]]}
    if args.qr:
        annotated, result = decode_qr(image)
        save_image(output / "qr.png", annotated)
        save_json(output / "qr.json", result)
        report["qr_decoded"] = result["decoded"]
    if args.faces:
        annotated, result = detect_faces(image, args.cascade)
        save_image(output / "faces.png", annotated)
        save_json(output / "faces.json", result)
        report["face_count"] = len(result["faces"])
    if args.ssd_model:
        annotated, result = detect_ssd(image, args.ssd_model, args.ssd_config, args.ssd_labels, args.confidence)
        save_image(output / "ssd.png", annotated)
        save_json(output / "ssd.json", result)
        report["ssd_count"] = len(result["detections"])
    if args.pose_model:
        annotated, result = detect_pose(image, args.pose_prototxt, args.pose_model, args.pose_format, args.pose_threshold)
        save_image(output / "pose.png", annotated)
        save_json(output / "pose.json", result)
        report["pose_visible_points"] = sum(point["xy"] is not None for point in result["keypoints"])
    save_json(output / "report.json", report)
    return report


def main(argv=None):
    parser = image_arguments(argparse.ArgumentParser(description=__doc__), 5)
    parser.add_argument("--min-area", type=float, default=200, help="Минимальная площадь красного контура, пиксель²")
    parser.add_argument("--s-min", type=int, default=80, help="Минимальная насыщенность красного 0..255")
    parser.add_argument("--v-min", type=int, default=60, help="Минимальная яркость красного 0..255")
    parser.add_argument("--kernel", type=int, default=3, help="Нечётный размер морфологического ядра 1..31")
    parser.add_argument("--qr", action="store_true", help="Найти и декодировать один обычный QR-код")
    parser.add_argument("--faces", action="store_true", help="Обнаружить лица Haar-каскадом; личность не определяется")
    parser.add_argument("--cascade", help="Путь к haarcascade_frontalface_default.xml при --faces")
    parser.add_argument("--ssd-model", help="TensorFlow frozen_inference_graph.pb из согласованного комплекта Yahboom")
    parser.add_argument("--ssd-config", help="Соответствующий ssd_mobilenet_v2_coco.txt/.pbtxt")
    parser.add_argument("--ssd-labels", help="object_detection_coco.txt; строка class_id-1, включая заполнители COCO")
    parser.add_argument("--confidence", type=float, default=0.4, help="Порог SSD 0..1 (по умолчанию %(default)s)")
    parser.add_argument("--pose-prototxt", help="Caffe OpenPose .prototxt для COCO18 или MPI15")
    parser.add_argument("--pose-model", help="Соответствующая модель OpenPose .caffemodel")
    parser.add_argument("--pose-format", choices=["coco", "mpi"], default="coco", help="Порядок точек: COCO18 или MPI15")
    parser.add_argument("--pose-threshold", type=float, default=0.1, help="Порог карты точки позы 0..1")
    return run_cli(parser, execute, argv)


if __name__ == "__main__":
    main()

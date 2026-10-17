# Источники и соответствие курсу Yahboom

Проверено при подготовке курса **17 октября 2026 года**. Это самостоятельные русские учебные материалы по последовательности производителя. Доступность пакетов определяется конкретным образом вашего ROSMASTER; пример из одной комплектации нельзя автоматически переносить на другую.

## Официальный маршрут 9.1–9.11

| Тема | Первичный источник | Как используется в практикуме |
|---|---|---|
| 9.1 | [Introduction to OpenCV](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8142/) | Чтение, пиксели, каналы, сохранение |
| 9.2 | [Geometric transformation](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8143/) | Масштабирование, поворот, affine/perspective |
| 9.3 | [Image processing](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8144/) | Рисование, пороги, края, морфология и цвет |
| 9.4 | [Image enhancement](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8145/) | Сглаживание, яркость и inpainting |
| 9.5 | [OpenCV applications](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8146/) | QR, OpenPose и TensorFlow MobileNetV2 COCO SSD |
| 9.6 | [Augmented reality](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8147/) | Шахматная доска, калибровка и AR |
| 9.7 | [AR QR code / ALVAR](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8148/) | Генерация и распознавание ALVAR/ARTag |
| 9.8 | [ROS image data](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8149/) | RGB/depth и cv_bridge |
| 9.9 | [ROS image processing](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8150/) | Узлы обработки потока |
| 9.10 | [Data conversion](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8151/) | LaserScan, PointCloud и PCD |
| 9.11 | [MediaPipe](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8152/) | Руки, поза, лицо; дополнительный подробный [вариант для Orin](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8293/) |

Главный каталог: [Yahboom ROSMASTER X3 Plus](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/). Официальный репозиторий производителя: [YahboomTechnology/ROSMASTERX3-PLUS](https://github.com/YahboomTechnology/ROSMASTERX3-PLUS). Большой заводской архив кода доступен через пункт **Download → Code** на главной странице; его не нужно загружать целиком для первого занятия. В первую очередь используйте уже установленное рабочее пространство стенда.

## Образ, ROS и камера

- [Orin: вход в Docker для ROS1](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/14316/) — подтверждает, что ROS1-курс Orin может выполняться внутри контейнера.
- [Raspberry Pi 5: Docker](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/11165/) — отдельная схема для Pi 5.
- [Удалённая работа/Jupyter](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8122/) — доступ к заводскому интерфейсу.
- [REP 151: Python 3](https://www.ros.org/reps/rep-0151.html) — переход ROS Noetic на Python 3; различия ROS-дистрибутивов.
- [sensor_msgs/Image](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/Image.html), [LaserScan](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/LaserScan.html), [PointCloud2](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/PointCloud2.html) — поля, кодировки и системы координат сообщений.
- [Исходники vision_opencv/cv_bridge](https://github.com/ros-perception/vision_opencv) — преобразование ROS-изображений в OpenCV.
- [ar_track_alvar](https://github.com/ros-perception/ar_track_alvar) — используемое семейство маркеров и ROS-пакет.

## OpenCV: первичная документация

- [Python tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html) — базовые операции и обработка изображений.
- [Геометрические преобразования](https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html).
- [Цветовые пространства и выделение цвета](https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html).
- [Морфологические операции](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html).
- [Сглаживание](https://docs.opencv.org/4.x/d4/d13/tutorial_py_filtering.html), [inpainting](https://docs.opencv.org/4.x/df/d3d/tutorial_py_inpainting.html).
- [Калибровка камеры](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html), [оценка позы](https://docs.opencv.org/4.x/d7/d53/tutorial_py_pose.html).
- [QRCodeDetector](https://docs.opencv.org/4.x/de/dc3/classcv_1_1QRCodeDetector.html).
- [Официальный пример DNN Pose](https://github.com/opencv/opencv/blob/4.x/samples/dnn/openpose.py) — подготовка Caffe-входа и извлечение ключевых точек.
- [OpenCV model zoo/configuration](https://github.com/opencv/opencv/blob/4.x/samples/dnn/models.yml) — согласование модели, конфигурации и входной обработки.

## MediaPipe Tasks

Заводские примеры могут использовать старый API `solutions`; новый вариант курса использует `HandLandmarker`, `PoseLandmarker`, `FaceLandmarker`. Модели для detector и landmarker — разные файлы.

- [Hand Landmarker: Python](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python).
- [Pose Landmarker: Python](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python).
- [Face Landmarker: Python](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python).

Официальные модели Google, версия URL `1`, которые загружает `tools/fetch_mediapipe_models.py`:

| Режим | Файл | Официальный URL |
|---|---|---|
| hands | `hand_landmarker.task` | [Скачать](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task) |
| pose | `pose_landmarker_lite.task` | [Скачать](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) |
| face | `face_landmarker.task` | [Скачать](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task) |

Например, из корня курса:

```bash
python3 tools/fetch_mediapipe_models.py --mode all
```

Эта команда явно обращается в интернет и сохраняет файлы в `models/`; остальные базовые опыты используют комплектные локальные данные. Соседний JSON содержит источник и вычисленный SHA256 загруженных байтов. Это запись контрольной суммы, а не проверка независимой подписи производителя.

## Учебные упрощения и границы

В 9.5 выделение красного цвета служит простым самостоятельным проектом. Оно не заменяет семантическое обнаружение SSD. Пример Caffe Pose относится к одному человеку и не реализует полноценную многопользовательскую сборку PAF. Веса подбираются к указанной конфигурации.

В 9.6 синтетическая доска показывает геометрию, но для метрической позы необходимы настоящие параметры камеры и физический размер клетки. В 9.7 ручная накладка не является обнаружением ALVAR. В 9.10 учебное облако не выдаётся за измерение LiDAR. В 9.11 нулевые обнаружения на пустой сцене сохраняются как нулевые.

Собственные материалы распространяются по [MIT](../LICENSE); сторонние материалы — по [своим лицензиям](../THIRD_PARTY.md). Конкретный статус проверки данной сборки приведён в [VALIDATION](VALIDATION.md).

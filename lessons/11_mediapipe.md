# 9.11. MediaPipe: кисть, поза и точки лица

[Назад: 9.10](10_data.md) · [Оглавление](../README.md)

**Результат:** собственное изображение с ключевыми точками, JSON с координатами и небольшой эксперимент по условиям обнаружения. Исходный кадр можно получить с ROSMASTER в уроке 9.8 и перенести на ноутбук. Ориентир: 60–90 минут.

## 1. Выберите совместимый путь

В заводских материалах Yahboom используются прежние MediaPipe Solutions: Hands, Pose, Holistic, FaceMesh и другие примеры. Современный путь MediaPipe Tasks использует объект задачи и отдельный файл модели. Это разные программные интерфейсы.

У нашего скрипта два явных режима: `--backend tasks` и `--backend legacy`. Первый предназначен для подготовленного ноутбука или уже совместимого окружения; второй — для установленной среды с `mp.solutions`. Скрипт не устанавливает пакеты и не загружает модели. Состояние API и поддержки старых решений следует сверять с документацией Google.

## 2. Подготовьте ноутбук для Tasks

Создайте отдельное окружение. Команды выполняются **на ноутбуке**, а не внутри заводского Python робота:

```bash
python3.11 -m venv .venv-mp
source .venv-mp/bin/activate
python -m pip install -r requirements-mediapipe-laptop.txt
python -c "import cv2, mediapipe as mp; print(cv2.__version__, mp.__version__)"
```

Используйте доступный Python 3.9–3.12, совместимый с закреплёнными пакетами; пример показывает Python 3.11. Подробности установки и активации для вашей ОС находятся в [инструкции настройки](../docs/SETUP_ROBOT.md). Файл зависимостей задаёт воспроизводимый учебный набор, а не обещание поддержки любого устройства. Он устанавливается в новое окружение, отдельно от OpenCV headless и заводских ROS-пакетов.

Скачайте нужную модель с официальной страницы Google и положите в `models/`. Для точных ссылок из этого курса можно выполнить готовую утилиту:

```bash
python tools/fetch_mediapipe_models.py --mode all
```

Команда обращается к официальному хранилищу Google. Соответствие задачи и модели должно быть точным:

| Задача скрипта | Модель | Имя файла для команд ниже |
|---|---|---|
| `hands` | [Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models) | `hand_landmarker.task` |
| `pose` | [Pose Landmarker Lite](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models) | `pose_landmarker_lite.task` |
| `face` | [Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker#models) | `face_landmarker.task` |

Для варианта `face` нужна именно модель Landmarker. Модель Face Detector решает другую задачу и не подходит этой команде.

## 3. Получите изображение и обнаружьте кисть

Сделайте резкий кадр своей раскрытой ладони или сохраните его с ROSMASTER. Создайте папку `student_photos/` и положите изображение в `student_photos/hand.jpg`. Эта папка исключена из обычного Git-коммита. Выполните:

```bash
python -m rosmaster_cv.lesson11_mediapipe --input student_photos/hand.jpg --mode hands --backend tasks --model models/hand_landmarker.task --output-dir outputs/11/hands
```

Откройте `landmarks.png` и `landmarks.json`. Скрипт переводит BGR OpenCV в RGB перед передачей модели и рисует результат собственными средствами OpenCV. Он не зависит от `solutions.drawing_utils` в режиме Tasks.

Если обнаружений ноль, это полноценный результат модели: проверьте размер ладони, резкость, освещение и фон. Не создавайте координаты вручную, чтобы получить красивую картинку. Сохраните неудачный кадр для сравнения и сделайте второй снимок.

## 4. Повторите для позы и лица

Подготовьте собственные `student_photos/person.jpg` с человеком в полный рост и `student_photos/face.jpg` с лицом:

```bash
python -m rosmaster_cv.lesson11_mediapipe --input student_photos/person.jpg --mode pose --backend tasks --model models/pose_landmarker_lite.task --output-dir outputs/11/pose
python -m rosmaster_cv.lesson11_mediapipe --input student_photos/face.jpg --mode face --backend tasks --model models/face_landmarker.task --output-dir outputs/11/face
```

X и Y ключевой точки заданы относительно размеров изображения. Например, x = 0.25 означает четверть ширины от левого края. Значение z зависит от модели и её системы нормирования; сохранённый здесь z нельзя трактовать как измеренное расстояние в метрах. У лица рисуются точки, у кисти и позы — выбранные анатомические связи.

Для локальной камеры ноутбука допустим ограниченный запуск. Подставьте проверенный индекс камеры; `0` здесь является примером:

```bash
python -m rosmaster_cv.lesson11_mediapipe --camera 0 --mode hands --backend tasks --model models/hand_landmarker.task --frames 20 --seconds 15 --output-dir outputs/11/camera
```

Файлы содержат последний кадр и результаты обработанных кадров. Записанное время обработки включает преобразование цвета, вызов модели и рисование. Каждый кадр обрабатывается независимо в IMAGE/static-режиме; последовательность не включает специальный видеотрекинг. На роботе удобнее использовать сохранённый ROS-кадр: активный ROS-драйвер уже может занимать устройство камеры.

## 5. Заводская среда ROSMASTER

Если в текущем интерпретаторе есть `mp.solutions`, можно выполнить учебный модуль так:

```bash
python3 -m rosmaster_cv.lesson11_mediapipe --input student_photos/hand.jpg --mode hands --backend legacy
```

Для установленного ROS1-пакета Yahboom основные примеры запускаются отдельно:

```bash
roslaunch yahboomcar_mediapipe 01_HandDetector.launch
roslaunch yahboomcar_mediapipe 02_PoseDetector.launch
roslaunch yahboomcar_mediapipe 03_Holistic.launch
roslaunch yahboomcar_mediapipe 04_FaceMesh.launch
roslaunch yahboomcar_mediapipe 05_FaceEyeDetection.launch
```

Выполняйте по одной команде, завершайте окно `q` или launch через Ctrl+C. В первоисточнике дополнительно разобраны `06_FaceLandmarks.py`, `07_FaceDetection.py`, `08_Objectron.py`, `09_VirtualPaint.py`, `10_HandCtrl.py`, `11_GestureRecognition.py`. Их окружения и совместимость относятся к конкретному заводскому образу; старый Objectron не является современной задачей Tasks. Контейнерные команды для своей комплектации берите из [инструкции настройки](../docs/SETUP_ROBOT.md) и страницы Orin.

## Задание и проверка

Сдайте три собственных изображения, результаты и таблицу «задача / модель / число обнаружений / время обработки». Для кисти сравните нормальное освещение, тень и частичное перекрытие. Объясните, почему нужны RGB, правильный файл модели и известный масштаб координат. Завершённая работа — воспроизводимый запуск с честно указанной средой и сохранёнными исходными кадрами.

**Источники:** [Yahboom 9.11](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8152/), [подробный вариант Orin](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8293/), [MediaPipe Hand Landmarker Python](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python), [MediaPipe Solutions и статус legacy](https://ai.google.dev/edge/mediapipe/solutions/guide), [официальный код Tasks HandLandmarker](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/hand_landmarker.py).

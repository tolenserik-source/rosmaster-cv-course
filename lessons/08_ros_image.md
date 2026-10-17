# 9.8. Получение RGB и глубины через ROS и cv_bridge

[Назад: 9.7](07_markers.md) · [Оглавление](../README.md) · [Далее: 9.9](09_ros_processing.md)

**Результат:** собственный кадр ROSMASTER, его метаданные и, при наличии глубинной камеры, исходный массив глубины. Ориентир: 45–60 минут. Эта работа показывает путь «драйвер камеры → ROS-сообщение → массив OpenCV → файл».

## 1. Проверьте среду и найдите данные

Все ROS-команды выполняются на роботе в его рабочей ROS1-среде, включая контейнер, если так устроен заводской образ. Само наличие Jetson Orin не определяет версию ROS. У ROS Noetic стандартный Python — Python 3, у Melodic стандартный — Python 2; готовность нужных модулей проверяют непосредственно:

```bash
python3 -c "import rospy, cv_bridge; print('Python 3 ROS bridge OK')"
rostopic list
```

Если импорт не проходит, сразу используйте завершённую заводскую ветку пункта 4. Установка `rospy` через pip не восстанавливает совместимость заводского ROS.

Найдите реальный **несжатый** топик изображения, проверьте его тип и частоту:

```bash
rostopic type /camera/rgb/image_raw
rostopic hz /camera/rgb/image_raw
```

Здесь и далее `/camera/rgb/image_raw` — имя из проверенного примера Yahboom; замените его, если ваш `rostopic list` показывает другое. Нужен тип `sensor_msgs/Image`. Топик с суффиксом `/compressed` имеет другой тип и не подходит этому скрипту. Частоту достаточно наблюдать несколько секунд, затем нажмите Ctrl+C.

Если камера ещё не запущена, выберите драйвер своего образа. В старой главе указан `roslaunch astra_camera astrapro.launch`, в главе Orin — `roslaunch orbbec_camera astraproplus.launch`. Запускайте соответствующую комплектации команду только один раз.

## 2. Сохраните цветной кадр

При успешном импорте Python 3:

```bash
python3 -m rosmaster_cv.lesson08_ros_image --topic /camera/rgb/image_raw --output outputs/08/frame.png
```

Скрипт ждёт одно сообщение до десяти секунд, преобразует его в `bgr8` и сохраняет PNG вместе с JSON. Окно GUI не требуется. В JSON указаны исходная кодировка, размер массива, тип данных, система координат и время сообщения.

Для простого преобразования изображения:

```bash
python3 -m rosmaster_cv.lesson08_ros_image --topic /camera/rgb/image_raw --invert --output outputs/08/inverted.png
```

Это инверсия яркостей каналов `255 − value`, а не геометрическое переворачивание кадра. Сравните два сохранённых изображения и объясните результат. Для повторных наблюдений задавайте новые имена, чтобы сохранить исходные снимки.

## 3. Получите глубину без потери исходных чисел

Если реально публикуется глубина:

```bash
rostopic type /camera/depth/image_raw
python3 -m rosmaster_cv.lesson08_ros_image --topic /camera/depth/image_raw --encoding passthrough --output outputs/08/depth.png
```

Получатся `depth.npy`, `depth.png` и `depth.json`. NPY хранит значения без преобразования. PNG — только нормированное изображение для просмотра. На нём яркость зависит от диапазона текущего кадра, поэтому измерять расстояния по этому PNG нельзя.

Посмотрите массив:

```bash
python3 -c "import numpy as np; a=np.load('outputs/08/depth.npy', allow_pickle=False); print(a.shape, a.dtype); print(a[a.shape[0]//2, a.shape[1]//2])"
```

Кодировка `16UC1` означает один канал 16-битных беззнаковых значений, `32FC1` — один канал 32-битных float. Само имя типа не подтверждает единицы конкретного драйвера. Проверьте документацию источника, затем сопоставьте число с расстоянием до плоского предмета. Нули, NaN и бесконечности часто обозначают отсутствие корректного измерения; их смысл также зависит от источника. Скрипт сохраняет их и запрещает инверсию глубины.

## 4. Завершённая заводская ветка для Melodic

Если Python 3 `cv_bridge` недоступен, используйте поставленные реализации, не меняя системный Python. После запуска подходящего драйвера:

```bash
roslaunch yahboomcar_visual astra_get_rgb.launch version:=cpp
```

Отдельно можно запустить:

```bash
roslaunch yahboomcar_visual astra_get_depth.launch version:=cpp
```

Откройте `rqt_graph`, найдите путь от камеры к узлу обработки, сохраните скриншот изображения и графа. Получите сведения о сообщении с помощью:

```bash
rostopic echo -n 1 /camera/rgb/image_raw/encoding
rostopic echo -n 1 /camera/rgb/image_raw/header
```

В главе также существует `version:=py`; её работоспособность зависит от заводского интерпретатора. C++-ветка позволяет выполнить наблюдение без собственного Python-моста.

## Задание и проверка

Сдайте RGB-кадр, его инверсию, таблицу «топик / тип / encoding / размер / frame_id». Для глубины добавьте NPY и объяснение единиц. В заводской ветке сдайте скриншоты RGB, глубины при её наличии и графа узлов. Объясните, зачем нужен `cv_bridge` и почему исходный depth-массив отличается от картинки для просмотра.

**Источники:** [Yahboom 9.8](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8149/), [вариант камеры Orin](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8290/), [sensor_msgs/Image](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/Image.html), [cv_bridge Python API](https://docs.ros.org/en/noetic/api/cv_bridge/html/python/), [ROS REP-151](https://www.ros.org/reps/rep-0151.html).

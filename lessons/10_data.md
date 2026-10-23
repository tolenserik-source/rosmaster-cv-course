# 9.10. LaserScan, облако точек и преобразования координат

**Работа на нашем роботе:** создайте [личную копию курса и выберите нужное окружение](../docs/SETUP_ROBOT.md). Все команды ниже выполняйте из её корня; результаты `outputs/` будут принадлежать вашей копии. Самостоятельный поиск камеры, контейнера и ROS-топиков разобран в той же инструкции.

[Назад: 9.9](09_ros_processing.md) · [Оглавление](../README.md) · [Далее: 9.11](11_mediapipe.md)

**Результат:** перевод лазерного скана в точки и растровый вид сверху; чтение облака из PCD или ROS; проверенное преобразование между системами координат. Первая часть полностью выполняется на ноутбуке. Для аппаратной части нужен работающий лидар или глубинная камера ROSMASTER. Ориентир: 90 минут.

## 1. Переведите расстояния в точки

Для луча с номером i угол равен `angle_min + i × angle_increment`. Координаты в системе сканера вычисляются как `x = r cos(angle)`, `y = r sin(angle)`, `z = 0`. В сообщении `LaserScan` углы заданы в радианах, расстояния — в метрах. Некорректные и выходящие за рабочий диапазон измерения нужно исключить.

Запустите демонстрацию:

```bash
python3 -m rosmaster_cv.lesson10_data --synthetic
```

Откройте `outputs/10/top_view.png` и `metadata.json`. Из 361 искусственного луча здесь остаются 349 допустимых точек. Искусственно пропущенные измерения демонстрируют фильтрацию. В `points.npy` находятся координаты Nx3. Это учебные числа, а не измерения робота.

На растровом изображении положительная ось x направлена вверх, y — влево. Предел по каждой оси по умолчанию ±5 м. Сравните:

```bash
python3 -m rosmaster_cv.lesson10_data --input-json outputs/10/synthetic_scan.json --extent 2 --output-dir outputs/10/cropped
```

Часть точек окажется вне картинки; поле `points_outside_raster` покажет их число. Исходные допустимые точки при этом остаются в NPY. Масштаб визуализации не изменяет измеренное расстояние.

## 2. Откройте облако точек

Первый запуск также создал `synthetic_cloud.pcd`: искусственную наклонную плоскость из 875 точек. Прочитайте её:

```bash
python3 -m rosmaster_cv.lesson10_data --pcd outputs/10/synthetic_cloud.pcd --pcd-units m --output-dir outputs/10/cloud
```

Формат PCD содержит описание полей и их типы. Учебный парсер поддерживает `DATA ascii` и координаты x, y, z; бинарный PCD он отклоняет с ясным сообщением. Универсального поля единиц в PCD нет, поэтому для чужого файла сначала выясните единицы, затем подтверждайте `--pcd-units m`.

Вид сверху отбрасывает высоту z. Посмотрите диапазоны координат:

```bash
python3 -c "import numpy as np; p=np.load('outputs/10/cloud/points.npy', allow_pickle=False); print(p.min(axis=0)); print(p.max(axis=0))"
```

Объясните, какая информация видна в массиве, но исчезает на картинке. Одно облако точек и его проекция ещё не задают карту SLAM: для объединения разных наблюдений необходимы их положения и согласованные координаты.

## 3. Проверьте преобразование координат

Жёсткое преобразование имеет вид `p_target = R p_source + t`. Матрица 4×4 объединяет поворот R и перенос t. Направление преобразования фиксируется явно: из `source_frame` в `target_frame`.

Для учебного поворота на 90° выполните:

```bash
python3 -m rosmaster_cv.lesson10_data --input-json outputs/10/synthetic_scan.json --transform-json outputs/10/synthetic_rotation.json --output-dir outputs/10/rotated
```

Сравните картинки и проверьте отдельную точку: при таком повороте `(1, 0, 0)` превращается в `(0, 1, 0)`. Эта матрица специально создана для искусственной сцены. Для настоящего робота берите преобразование из проверенной TF-цепочки или измеренной внешней калибровки. Расстояния между камерой и лидаром нельзя назначать по внешнему виду платформы. Скрипт проверяет имена систем и отклоняет масштабирование вместо жёсткого поворота.

## 4. Получите настоящие ROS-данные

В заводской ROS1-среде:

```bash
python3 -c "import rospy; from sensor_msgs import point_cloud2; print('ROS data OK')"
rostopic list
```

Найдите реальные топики и проверьте их тип. Примеры Yahboom:

```bash
rostopic type /scan
python3 -m rosmaster_cv.lesson10_data --scan-topic /scan --output-dir outputs/10/robot_scan
```

Для существующего `sensor_msgs/PointCloud2`:

```bash
python3 -m rosmaster_cv.lesson10_data --cloud-topic /camera/depth_registered/points --output-dir outputs/10/robot_cloud
```

Каждый запуск получает одно сообщение с полным пределом ожидания десять секунд, включая запуск ROS. Для облака читаются первые допустимые точки до `--max-points 200000`; сведения о лимите записываются в JSON. Название камеры замените на фактически найденное. Сверьте `frame_id`, единицы драйвера и ориентацию осей.

## 5. Заводская ветка и Melodic

При отсутствии Python 3 ROS-модулей используйте существующие программы:

```bash
roslaunch yahboomcar_visual laser_to_image.launch
```

При работающем `/scan` результат публикуется в `/laserImage`. Для искусственного облака:

```bash
roslaunch yahboomcar_visual pointCloud_pub.launch use_rviz:=true
```

Для реального существующего облака:

```bash
roslaunch yahboomcar_visual pointCloud_visualize.launch cloud_topic:=/camera/depth_registered/points
```

Останавливайте примеры Ctrl+C после наблюдения. Для короткой записи PCD можно выполнить `timeout 3s rosrun pcl_ros pointcloud_to_pcd input:=/camera/depth_registered/points` в отдельной папке результатов. Команда запишет несколько кадров; код завершения 124 означает срабатывание ограничения `timeout`. Если файлы бинарные, анализируйте их средствами PCL или сначала экспортируйте ASCII.

## Задание и проверка

Сдайте скан, облако и повёрнутую сцену с JSON, таблицу единиц и направлений осей, одно ручное вычисление x/y и одного преобразования. На роботе добавьте реальный `frame_id` и скриншот; в заводской ветке — RViz и `/laserImage`. Объясните, почему пиксели вида сверху не являются исходными метрами и почему нельзя автоматически совмещать лидар и камеру.

**Источники:** [Yahboom 9.10](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/8151/), [LaserScan](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/LaserScan.html), [PointCloud2](https://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/PointCloud2.html), [PCL: формат PCD](https://pointclouds.org/documentation/tutorials/pcd_file_format.html), [ROS REP-103](https://www.ros.org/reps/rep-0103.html).

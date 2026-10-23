# Подготовка ROSMASTER и ноутбука

Вы самостоятельно определите окружение, проверите устройства, запустите программу и откроете результат. Заполняйте [паспорт](../templates/ROBOT_PASSPORT.md) по выводу своих команд: это ваш журнал проверок. Неизвестное значение отмечайте «не проверено». Наличие терминала ещё не означает, что в нём загружен нужный ROS.

## 0. Подключитесь и создайте личную копию

На ноутбуке в PowerShell или терминале Linux/macOS:

```bash
ssh jetson@192.168.1.185
```

Введите действующий пароль своей учётной записи либо используйте настроенный SSH-ключ. Символы пароля не отображаются; пароль и ключи не включаются в отчёт. Ошибки входа разобраны в [диагностике подключения](TROUBLESHOOTING.md#подключение-и-перезагрузка).

Первый урок можно выполнить в общей папке по его инструкции. **Для остальных занятий и изменения кода создайте личную копию**. В командах ниже замените `ivanov` на уникальную фамилию латиницей или номер команды. На роботе, после входа по SSH:

```bash
mkdir -p /home/jetson/temp/students/ivanov
git clone https://github.com/tolenserik-source/rosmaster-cv-course.git /home/jetson/temp/students/ivanov/rosmaster-cv-course
cd /home/jetson/temp/students/ivanov/rosmaster-cv-course
pwd
ls data/scene.png rosmaster_cv/lesson01_intro.py
```

Клонирование нужно один раз. Если каталог уже существует, перейдите в него командой `cd` и проверьте файлы; не удаляйте свою работу. Если интернета нет, но общая копия курса существует, вместо сетевого клонирования в ещё не существующую папку выполните:

```bash
git clone --no-hardlinks /home/jetson/rosmaster-cv-course /home/jetson/temp/students/ivanov/rosmaster-cv-course
```

Все последующие пути `data/`, `outputs/` и `student_photos/` относятся к вашей копии. Изменяйте код здесь. На нашем стенде `/home/jetson/temp` подключена в существующий контейнер как `/root/temp`; поэтому ваши файлы доступны в обеих средах.

## 1. Определите, где открыт терминал

Есть три разных места выполнения: **ваш ноутбук**, **основная система робота** и **заводской контейнер на роботе**. Файлы, библиотеки и доступные устройства могут отличаться. В отчёте укажите, где запущена программа.

В терминале робота выполните:

```bash
uname -m
cat /etc/os-release
python3 --version
printenv ROS_VERSION ROS_DISTRO ROS_PYTHON_VERSION
```

Отсутствие вывода `printenv` не доказывает, что ROS не установлен: возможно, его окружение ещё не загружено. Выполните диагностику из папки курса:

```bash
python3 tools/doctor.py
python3 -c "import cv2, numpy; print(cv2.__version__, numpy.__version__)"
```

Если NumPy и OpenCV импортируются, уроки 9.1–9.6 можно начать на комплектных данных. Для ROS-уроков дополнительно:

```bash
python3 -c "import rospy; from cv_bridge import CvBridge; print('ROS Python 3 bridge: OK')"
```

Не заменяйте эту проверку наличием только команды `roslaunch`: она может использовать другой Python.

## 2. Выберите существующий маршрут стенда

| Результат проверки | Как действовать |
|---|---|
| ROS1 Noetic и Python 3 bridge доступны | Используйте программы курса; найдите топики командами из шага 4 и запишите их в паспорт |
| ROS1 работает внутри заводского Docker | Проверьте контейнер и войдите в него по командам ниже; повторите импорты внутри |
| ROS1 Melodic, `roslaunch` работает, Python 3 bridge отсутствует | Базовый OpenCV выполняйте на Python 3; для 9.7–9.10 используйте заводские варианты, приведённые в соответствующих уроках |
| Обнаружен ROS2 | Выполните `docker ps -a` и найдите ROS1-контейнер. Наш host использует Humble, контейнер — Noetic. ROS2-порт этих узлов в комплект не входит |
| ROS отсутствует на ноутбуке | Выполняйте подготовительные упражнения на файлах; настоящие ROS-опыты завершите на стенде |

У производителя есть варианты ROS1 в Docker для Orin и Raspberry Pi 5. Название платы само по себе не определяет версию ROS. Официальные ссылки: [Orin Docker](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/14316/), [Pi 5 Docker](https://www.yahboom.net/study/ROSMASTER-X3-PLUS/11165/).

Для просмотра уже существующих контейнеров, если Docker доступен пользователю:

```bash
docker ps -a
```

На нашем роботе существует контейнер **`busy_yalow`** с ROS1 Noetic. Перед его запуском на host проверьте, что он запускает и какие файлы/устройства получает:

```bash
docker inspect --format '{{json .Config.Entrypoint}} {{json .Config.Cmd}}' busy_yalow
docker inspect --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' busy_yalow
docker inspect --format '{{json .HostConfig.Devices}}' busy_yalow
```

При проверке 23.10.2026 командой контейнера была `/bin/bash`, общая папка — `/home/jetson/temp -> /root/temp`. Сверьте каждый `PathOnHost` и каждый источник `/dev/...` из `Mounts` с существующим путём через `ls -l`: USB-устройство не должно оказаться отсутствующим путём или обычной папкой. При несовпадении остановитесь на диагностике подключений из шага 4; не запускайте контейнер для работы с этим датчиком. Если конфигурация отличается и запускает неизвестную программу управления платформой, сначала прочитайте её исходник. Этот курс не требует запуска приводов.

Если статус контейнера `Exited`, а конфигурация соответствует ожидаемой, запустите существующий контейнер:

```bash
docker start busy_yalow
```

Если статус уже `Up`, пропустите `docker start`. Вход и переход в личную папку:

```bash
docker exec -it busy_yalow bash
cd /root/temp/students/ivanov/rosmaster-cv-course
pwd
ls data/scene.png
```

Теперь команды выполняются **в контейнере**. `exit` возвращает на host и не останавливает контейнер. Если папка не видна, сравните `Mounts` и путь из шага 0: вход в контейнер не переносит файлы автоматически. На другом стенде имя контейнера выбирается по выводу `docker ps -a`, а пути — по `docker inspect`.

Если контейнера нет, зафиксируйте результат и выполняйте файловую часть курса на host/ноутбуке. Для ROS1 нужна отдельная установка совместимого окружения по документации своего образа, ссылки приведены выше. Не запускайте неизвестный `run_docker.sh` вместо диагностики: он может создавать новый контейнер с другими устройствами.

## 3. Загрузите ROS-окружение в текущем терминале

Сначала посмотрите, какие установки реально существуют:

```bash
ls /opt/ros
```

Если там действительно есть `noetic`, пример для **текущего терминала**:

```bash
source /opt/ros/noetic/setup.bash
```

В контейнере нашего стенда затем загрузите рабочие пространства:

```bash
source /root/yahboomcar_ws/devel/setup.bash --extend
source /root/software/library_ws/devel/setup.bash --extend
source /root/software/ar_track_ws/devel/setup.bash --extend
printenv ROS_VERSION ROS_DISTRO
python3 -c "import rospy; from cv_bridge import CvBridge; print('ROS Python 3 bridge: OK')"
```

Ожидаются `1`, `noetic` и `ROS Python 3 bridge: OK`. Повторяйте загрузку окружения в каждом новом терминале контейнера. Если на другом образе установлен `melodic`, выбирайте его setup. Отсутствующий путь можно найти командой `find /opt/ros /root/yahboomcar_ws /root/software -maxdepth 5 -name setup.bash -type f 2>/dev/null`. Загружайте рабочие пространства своего дистрибутива; не смешивайте ROS1 и ROS2 и не переписывайте `.bashrc` ради одного занятия.

Проверьте пакеты:

```bash
rospack find yahboomcar_visual
rospack find cv_bridge
```

Проверка связи с ROS master в Linux:

```bash
timeout 8s rostopic list
```

Если список топиков получен, master уже работает. Если связи нет, выполните `printenv ROS_MASTER_URI ROS_IP ROS_HOSTNAME` и `pgrep -af rosmaster`. При существующем процессе исправьте окружение текущего терминала, не создавая второй master. Для опыта, где все ROS-процессы работают на одном роботе, ошибочный адрес другого компьютера можно заменить на `export ROS_MASTER_URI=http://127.0.0.1:11311`, затем `unset ROS_IP ROS_HOSTNAME` и повторить проверку. Для распределённого ROS нужен реальный сетевой адрес master.

Если master и его процесс отсутствуют, откройте второе SSH-окно, войдите в тот же контейнер, загрузите те же setup-файлы и выполните `roscore`. Оставьте окно открытым. В рабочем окне повторите `rostopic list`. В конце завершите свои ROS-программы, затем свой `roscore` через Ctrl+C. Другие работающие процессы не останавливайте.

## 4. Проверьте настоящую камеру

У ROSMASTER могут отличаться RGBD-камера, USB-камера и соответствующие драйверы. Для OpenCV-пути определите доступные устройства:

```bash
ls -l /dev/video*
```

Не каждый `/dev/videoN` выдаёт RGB. На host нашего стенда проверен путь `/dev/camera_usb`; `/dev/camera_depth` также выдавал цветные UVC-кадры, что не означает измерение глубины. Проверьте текущие устройства и занятость:

```bash
ls -l /dev/camera_usb /dev/camera_depth
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/camera_usb --list-formats-ext
fuser -v /dev/camera_usb
```

`v4l2-ctl` установлен на нашем роботе. Если на другом компьютере его нет, посмотрите `/dev/v4l/by-id/` и документацию камеры. Если `fuser` показывает PID, выясните команду через `ps -p ЧИСЛО_PID -o pid,user,args`. Завершите своё предыдущее приложение через Ctrl+C либо используйте уже работающий ROS-топик; чужие процессы не завершайте. На свободном устройстве, **на host из личной папки курса**:

```bash
timeout 15s python3 tools/capture.py --source /dev/camera_usb --frames 5 --save-every 1 --out outputs/camera_check
cat outputs/camera_check/capture.json
```

Ожидаются пять PNG и `frames_read: 5`. Скачайте и откройте их по шагу 5; только реальный кадр подтверждает выбор камеры. Запишите источник и разрешение в свой паспорт. После перезагрузки проверьте пути заново. Если кадры не получены, перейдите к [диагностике](TROUBLESHOOTING.md); видеоупражнения доступны также с `data/demo.avi`.

Если камера уже работает через ROS, читайте её топик. Возможные заводские launch-файлы **являются вариантами, а не списком команд для совместного запуска**:

| Проверенный установленный пакет | Пример варианта драйвера |
|---|---|
| `astra_camera` | `astrapro.launch` либо `astraproplus.launch` по модели камеры |
| `orbbec_camera` | `astraproplus.launch` в соответствующих новых образах |
| `usb_cam` | `usb_cam-test.launch` для выбранной USB-камеры |

Выберите драйвер по модели своей камеры и проверьте установленный файл. Для USB-камеры нашего стенда, в ROS1-контейнере:

```bash
roslaunch --files usb_cam usb_cam-test.launch
cat "$(rospack find usb_cam)/launch/usb_cam-test.launch"
```

Сверьте `video_device`, разрешение и формат с проверкой выше. Если значения не подходят, скопируйте launch в свою папку: `cp "$(rospack find usb_cam)/launch/usb_cam-test.launch" ./usb_cam_course.launch`, отредактируйте `nano usb_cam_course.launch` и запускайте `roslaunch ./usb_cam_course.launch`. Если значения совпадают, используйте `roslaunch usb_cam usb_cam-test.launch`. Оставьте терминал открытым; дальнейшие проверки выполняйте во втором окне того же контейнера с загруженным ROS. Камеру должен открывать один процесс. Перед запуском ALVAR проверьте `<include>`: его launch уже может включать драйвер.

**RGBD нашего стенда пока не принят:** 23.10.2026 найдены устаревшие USB-пути контейнера, depth-поток не подтверждён, наблюдались перезагрузки. Сравните `lsusb`, `readlink -f /dev/astro_pro_plus` на host и `docker inspect` из шага 2. При несовпадении сохраните диагностику. Не создавайте фиктивные ссылки на старые USB-адреса и не повторяйте падающий драйвер циклически. Исправление подключений контейнера — отдельная техническая работа с повторной проверкой оборудования; RGB- и файловые упражнения выполняются независимо.

Найдите реальные топики и проверьте тип:

```bash
timeout 8s rostopic list
rostopic find sensor_msgs/Image
rostopic find sensor_msgs/CameraInfo
rostopic find sensor_msgs/LaserScan
rostopic find sensor_msgs/PointCloud2
rostopic type /ФАКТИЧЕСКИЙ_ТОПИК_ИЗОБРАЖЕНИЯ
timeout 8s rostopic hz /ФАКТИЧЕСКИЙ_ТОПИК_ИЗОБРАЖЕНИЯ
```

В последних двух командах замените `/ФАКТИЧЕСКИЙ_ТОПИК_ИЗОБРАЖЕНИЯ` именем из вывода `rostopic find sensor_msgs/Image`. Например, используйте `/usb_cam/image_raw` только если оно присутствует. Отсутствие топика означает, что источник ещё не публикует поток.

Урок 9.8 ожидает обычный `sensor_msgs/Image`; `sensor_msgs/CompressedImage` — другой тип. Для RGB используется `bgr8`, для depth — `passthrough`. Depth-картинка может быть 16-битной или содержать вещественные значения, поэтому сохраняется исходный NPY. Единицы глубины определяются драйвером и кодировкой; нельзя автоматически объявлять все значения миллиметрами.

## 5. Работа через SSH, VNC и Jupyter

Курс сохраняет PNG/JSON/CSV. В новом **локальном PowerShell на ноутбуке** скачайте результаты своей копии:

```powershell
New-Item -ItemType Directory -Force "$HOME\Downloads\rosmaster-results\ivanov" | Out-Null
Set-Location "$HOME\Downloads\rosmaster-results\ivanov"
scp -r jetson@192.168.1.185:/home/jetson/temp/students/ivanov/rosmaster-cv-course/outputs .
Start-Process .\outputs\camera_check\frame_0001.png
```

Последняя команда подходит после успешной проверки камеры. Для другого опыта откройте его PNG в скачанной папке `outputs`. На Linux/macOS создайте локальную папку, перейдите в неё и выполните ту же команду `scp`, затем откройте файлы файловым менеджером. Повторное скачивание обновляет одноимённые результаты. Контейнерный `/root/temp/students/ivanov/...` виден на host как `/home/jetson/temp/students/ivanov/...`.

**Jupyter — дополнительный интерфейс.** На host выполните `jupyter server list` или `jupyter notebook list`. Вывод может содержать token: используйте его только локально для входа, не сохраняйте в отчёт. Если сервер не запущен и команда `jupyter` установлена, из личной папки курса запустите:

```bash
jupyter lab --no-browser --ip=127.0.0.1 --port=8889
```

В отдельном терминале **ноутбука** создайте туннель:

```bash
ssh -N -L 8889:127.0.0.1:8889 jetson@192.168.1.185
```

Откройте `http://127.0.0.1:8889` в браузере ноутбука и введите token из вывода Jupyter. Если порт занят, выберите свободный порт и замените его в команде сервера, обоих числах туннеля и URL. Завершайте свои сервер и туннель через Ctrl+C в соответствующих окнах. Если сервер уже работает, используйте его фактический локальный адрес/порт из списка и соответствующий SSH-туннель.

Проверьте Python ядра:

```python
import sys
print(sys.executable)
import cv2
print(cv2.__version__)
```

Host-ядро не получает ROS1-библиотеки от одного наличия контейнера. Для ROS используйте терминал контейнера либо уже доступное ядро с успешным импортом `rospy` и `cv_bridge`. Папка блокнота должна содержать курс или находиться в его `notebooks/`.

Через обычный SSH используйте сохранение файлов и `rostopic`. Для launch с параметром `open_rviz` можно указать `open_rviz:=false`. RViz и другие GUI-примеры требуют рабочего стола робота или рабочего графического подключения; обязательный файловый маршрут не требует настройки VNC.

## 6. Установка на личном ноутбуке

Этот маршрут предназначен для нового виртуального окружения с **CPython 3.9–3.12**. Учебные версии зависимостей закреплены для воспроизводимости; они не объявляются самыми новыми. Если у вас Python 3.13 или новее, установите параллельно Python 3.12 и выберите его для этого проекта.

**Linux/macOS**, из корня папки курса:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-laptop.txt
python tools/doctor.py
python -m rosmaster_cv.lesson01_intro --input data/scene.png --out outputs/01
```

**Windows PowerShell**, если установлен Python 3.12 и доступен launcher `py`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-laptop.txt
.\.venv\Scripts\python.exe tools/doctor.py
.\.venv\Scripts\python.exe -m rosmaster_cv.lesson01_intro --input data/scene.png --out outputs/01
```

Явный путь к Python в Windows позволяет обойти необходимость менять политику выполнения PowerShell. Если `py` отсутствует, используйте путь к установленному Python 3.12.

В одном окружении устанавливайте только один вариант OpenCV wheel. `opencv-python`, `opencv-contrib-python` и headless-варианты используют общее имя импорта `cv2`. В этом курсе ноутбук использует contrib, а отдельная среда автоматической проверки — contrib-headless.

Для блокнотов на ноутбуке, в этом же **новом** окружении:

```bash
python -m pip install jupyterlab
python -m jupyterlab
```

Для MediaPipe создайте отдельное окружение `.venv-mp`, установите `requirements-mediapipe-laptop.txt` и следуйте [уроку 9.11](../lessons/11_mediapipe.md). Наличие пакета на x86_64-ноутбуке не означает, что такой же wheel доступен для старой ARM-системы робота; для неё предусмотрены заводские примеры.

## Готовность к занятиям

Самостоятельно отметьте выполненные проверки. Стенд готов к первому уроку, когда выполнен `doctor.py`, открывается `data/scene.png`, создаётся результат 9.1 и студент знает, в каком окружении находится. К ROS-урокам дополнительно должны быть подтверждены master, Python bridge либо заводской маршрут, камера, нужные топики и доступ к результатам. Полный список полей: [паспорт](../templates/ROBOT_PASSPORT.md).

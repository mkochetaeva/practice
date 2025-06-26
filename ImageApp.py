import sys
import cv2
import os
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                      QComboBox, QSpinBox, QMessageBox, QSlider)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer


class ImageProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Фоторедактор")
        self.setGeometry(100, 100, 900, 700)

        # инициализация переменных
        self.original_image = None
        self.processed_image = None
        self.camera = None
        self.last_directory = ""

        # создание интерфейса
        self.create_ui()

    def create_ui(self):
        # главный виджет
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # область отображения изображения
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        layout.addWidget(self.image_label)

        buttons_layout = QHBoxLayout()

        # кнопка загрузки из файла
        self.load_button = QPushButton("Загрузить изображение")
        self.load_button.clicked.connect(self.load_image)
        buttons_layout.addWidget(self.load_button)

        # кнопка камеры
        self.camera_button = QPushButton("Использовать камеру")
        self.camera_button.clicked.connect(self.toggle_camera)
        buttons_layout.addWidget(self.camera_button)

        # кнопка захвата с камеры
        self.capture_button = QPushButton("Сделать снимок")
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setVisible(False)
        buttons_layout.addWidget(self.capture_button)

        layout.addLayout(buttons_layout)

        # цветовой канал
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Цветовой канал:"))

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["Оригинал", "Красный", "Зеленый", "Синий", "Черно-белый"])
        self.channel_combo.currentIndexChanged.connect(self.show_channel)
        channel_layout.addWidget(self.channel_combo)

        layout.addLayout(channel_layout)

        # управление обрезкой
        crop_layout = QHBoxLayout()
        crop_layout.addWidget(QLabel("Обрезка (x,y,ширина,высота):"))

        # поля ввода координат
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        crop_layout.addWidget(self.x_spin)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 10000)
        crop_layout.addWidget(self.y_spin)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        crop_layout.addWidget(self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        crop_layout.addWidget(self.height_spin)

        # кнопка обрезки
        self.crop_button = QPushButton("Обрезать")
        self.crop_button.clicked.connect(self.crop_image)
        crop_layout.addWidget(self.crop_button)

        layout.addLayout(crop_layout)

        # управление яркостью
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Яркость:"))

        # слайдер для регулировки яркости
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        brightness_layout.addWidget(self.brightness_slider)

        # отображение текущего значения
        self.brightness_value = QLabel("0")
        brightness_layout.addWidget(self.brightness_value)

        # кнопка применения изменений
        self.brightness_button = QPushButton("Применить")
        self.brightness_button.clicked.connect(self.adjust_brightness)
        brightness_layout.addWidget(self.brightness_button)

        self.brightness_slider.valueChanged.connect(
            lambda: self.brightness_value.setText(str(self.brightness_slider.value())))

        layout.addLayout(brightness_layout)

        # инструмент создания линий
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("Линия (x1,y1,x2,y2,толщина):"))

        # поля координат линии
        self.x1_spin = QSpinBox()
        self.x1_spin.setRange(0, 10000)
        line_layout.addWidget(self.x1_spin)

        self.y1_spin = QSpinBox()
        self.y1_spin.setRange(0, 10000)
        line_layout.addWidget(self.y1_spin)

        self.x2_spin = QSpinBox()
        self.x2_spin.setRange(0, 10000)
        line_layout.addWidget(self.x2_spin)

        self.y2_spin = QSpinBox()
        self.y2_spin.setRange(0, 10000)
        line_layout.addWidget(self.y2_spin)

        # поле ввода толщины линии
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 20)
        self.thickness_spin.setValue(2)
        line_layout.addWidget(self.thickness_spin)

        # кнопка рисования линии
        self.line_button = QPushButton("Нарисовать линию")
        self.line_button.clicked.connect(self.draw_line)
        line_layout.addWidget(self.line_button)

        layout.addLayout(line_layout)

        # ryjgrf c,hjcf bpvtytybq
        self.reset_button = QPushButton("Сбросить изменения")
        self.reset_button.clicked.connect(self.reset_image)
        layout.addWidget(self.reset_button)

    def load_image(self):
        self.stop_camera()

        # указываем пустую строку в качестве начальной директории, чтобы можно было выбрать любую папку
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*)"  # Добавлены дополнительные форматы
        )

        if not file_path: # пользователь отменил выбор
            return

        try:
            # обработка длинных путей
            if os.name == 'nt':
                file_path = str(Path(file_path).resolve())

            # проверяем доступ к файлу
            if not os.access(file_path, os.R_OK):
                raise PermissionError("Нет прав на чтение файла")

            # читаем изображение с проверкой
            self.original_image = cv2.imread(file_path)
            if self.original_image is None:
                raise ValueError(f"Не удалось прочитать файл изображения: {file_path}")

            # конвертируем цветовое для отображения
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            self.display_image()

            # уст параметры обрезки
            height, width = self.original_image.shape[:2]
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            self.x_spin.setMaximum(width - 1)
            self.y_spin.setMaximum(height - 1)

            # Сохраняем папку для следующего использования
            self.last_directory = os.path.dirname(file_path)

            QMessageBox.information(self, "Успех", "Изображение успешно загружено")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки изображения:\n{str(e)}")


    def toggle_camera(self):
        if self.camera is None:
            # подключение к камере
            self.camera = cv2.VideoCapture(0)

            if not self.camera.isOpened():
                self.camera = None
                QMessageBox.critical(self, "Ошибка",
                                     "Не удалось подключиться к камере. Возможные решения:\n"
                                     "1. Проверьте подключение камеры\n"
                                     "2. Предоставьте права доступа\n"
                                     "3. Попробуйте другую камеру\n"
                                     "4. Перезапустите приложение")
                return

            # обновляем интерфейс
            self.camera_button.setText("Остановить камеру")
            self.capture_button.setVisible(True)

            # таймер для обновления изобр
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_camera)
            self.timer.start(30) # 30 сек
        else:
            self.stop_camera()

    def update_camera(self):
        # обновление изобр с камеры
        ret, frame = self.camera.read()
        if ret:
            # конвертируем изобр для отображения
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w

            # создаем QImage и отображаем его
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(
                QPixmap.fromImage(q_img).scaled(
                    self.image_label.width(),
                    self.image_label.height(),
                    Qt.KeepAspectRatio
                )
            )

    def stop_camera(self):
        # остановка камеры
        if hasattr(self, 'timer') and self.timer is not None:
            self.timer.stop()
        if self.camera is not None:
            self.camera.release()
            self.camera = None

        #возвращаем исходное состояние кнопки
        self.camera_button.setText("Использовать камеру")
        self.capture_button.setVisible(False)

    def capture_image(self):
        #захват изображения с камеры
        if self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                self.stop_camera()
                self.original_image = frame.copy()
                self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
                self.display_image()

                #обновление параметров обрезки
                height, width = self.original_image.shape[:2]
                self.width_spin.setValue(width)
                self.height_spin.setValue(height)

    def display_image(self):
        # отображение текущего изображения в интерфейсе
        if self.processed_image is not None:
            h, w, ch = self.processed_image.shape
            bytes_per_line = ch * w

            # создаем QImage из  данных OpenCV
            q_img = QImage(self.processed_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

            # масштабируем и отображаем изобр
            self.image_label.setPixmap(
                QPixmap.fromImage(q_img).scaled(
                    self.image_label.width(),
                    self.image_label.height(),
                    Qt.KeepAspectRatio
                )
            )

    def show_channel(self):
        # отображение выбраного цветового канала
        if self.original_image is None:
            return

        channel = self.channel_combo.currentIndex()

        if channel == 0:  # оригинал
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        elif channel == 4:  # ч/б
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            self.processed_image = cv2.cvtColor(self.processed_image, cv2.COLOR_GRAY2RGB)
        else:
            # разделяем изображения на каналы
            b, g, r = cv2.split(self.original_image)
            zeros = np.zeros_like(b)

            if channel == 1:  # красный
                self.processed_image = cv2.merge([zeros, zeros, r])
            elif channel == 2:  # зеленый
                self.processed_image = cv2.merge([zeros, g, zeros])
            elif channel == 3:  # синий
                self.processed_image = cv2.merge([b, zeros, zeros])

            # конвертируем обратно в rgb  и отображения
            self.processed_image = cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2RGB)

        self.display_image()

    def crop_image(self):
        # обрезка изображения по заданным координатам
        if self.original_image is None:
            return

        #параметры обрезки
        x = self.x_spin.value()
        y = self.y_spin.value()
        width = self.width_spin.value()
        height = self.height_spin.value()

        # размеры изображения
        img_height, img_width = self.original_image.shape[:2]

        # проверяем, что область обрезки не выходит за границы
        if x >= img_width or y >= img_height:
            QMessageBox.warning(self, "Предупреждение", "Область обрезки выходит за границы изображения")
            return

        # корректировка размеров, если те выходят за границы
        if x + width > img_width:
            width = img_width - x
        if y + height > img_height:
            height = img_height - y

        # проверка валиднсти размеров после корректировки
        if width <= 0 or height <= 0:
            QMessageBox.warning(self, "Ошибка", "Недопустимые области обрезки")
            return

        # обрезка
        cropped = self.original_image[y:y + height, x:x + width]
        self.original_image = cropped.copy()
        self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

        # обновление параметров в интерфейсе
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)

        self.display_image()

    def adjust_brightness(self):
        # корректировка яркости изобр
        if self.original_image is None:
            return

        value = self.brightness_slider.value()

        # конвертируем в HSV
        hsv = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # измеряем яркость
        v = cv2.add(v, value)
        v = np.clip(v, 0, 255)

        # объединение каналов обратно
        hsv = cv2.merge((h, s, v))

        # конверитруем обратно в bgr
        self.original_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

        self.display_image()

    def draw_line(self):
        # рисование линии на изображении
        if self.original_image is None:
            return

        # параметры линии
        x1 = self.x1_spin.value()
        y1 = self.y1_spin.value()
        x2 = self.x2_spin.value()
        y2 = self.y2_spin.value()
        thickness = self.thickness_spin.value()

        # размеры изображения
        height, width = self.original_image.shape[:2]

        # проверяем, что координаты внутри изображения
        if (x1 >= width or y1 >= height or x2 >= width or y2 >= height or
                x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0):
            QMessageBox.warning(self, "Предупреждение", "Координаты линии выходят за границы изображения")
            return

        # создаем копию изобр и рисуем линию
        image_with_line = self.original_image.copy()
        cv2.line(image_with_line, (x1, y1), (x2, y2), (0, 255, 0), thickness)

        # обновляем изображение
        self.original_image = image_with_line.copy()
        self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.display_image()

    def reset_image(self):
        # сброс всех изменений
        if self.original_image is not None:
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            self.display_image()
            self.channel_combo.setCurrentIndex(0)
            self.brightness_slider.setValue(0)

    def closeEvent(self, event):
        # закрыть окно
        self.stop_camera()
        event.accept()

if __name__ == "__main__":
    # создание и запуск приложения 
    app = QApplication(sys.argv)
    window = ImageProcessorApp()
    window.show()
    sys.exit(app.exec_())

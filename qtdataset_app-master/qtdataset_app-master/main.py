import sys
import cv2
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRegularExpression, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QImage, QRegularExpressionValidator
from PySide6.QtWidgets import QApplication, QLabel, QGridLayout, QWidget, QPushButton, QLineEdit, QVBoxLayout
from pyzbar.pyzbar import decode  # Библиотека считывания шрих-кодов
import numpy as np
# TODO: на данный момент библиотека pyzbar работает только с черно-белой камерой. Нужно разобраться почему так
import uuid


# Инициализация виджета камеры
class CameraWorker(QThread):
    image_data = Signal(QImage)

    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.capture = cv2.VideoCapture(self.camera_id)
        _, self.frame = self.capture.read()
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 4096)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.is_running = True

    def run(self):
        while self.is_running:
            ret, self.frame = self.capture.read()
            if ret:
                rgb_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(rgb_image, (320, 240))
                h, w, ch = resized.shape
                image = QImage(resized.data, w, h, ch * w, QImage.Format_RGB888)
                self.image_data.emit(image)

    def stop(self):
        self.is_running = False


class CameraWidget(QWidget):
    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.label = QLabel()

        self.current_image = None

        self.camera_worker = CameraWorker(self.camera_id)
        self.camera_worker.image_data.connect(self.update_image)
        self.camera_worker.start()

    @Slot(QImage)
    def update_image(self, image):
        self.current_image = image
        pixmap = QPixmap.fromImage(image)
        self.label.setPixmap(pixmap)

    def take_photo(self, code):
        filename = f"Dataset/{code}/{self.camera_id}_{uuid.uuid1()}.jpg"
        cv2.imwrite(filename, self.camera_worker.frame)

    def read_barcode(self):
        frame_gray = cv2.cvtColor(self.camera_worker.frame, cv2.COLOR_BGR2GRAY)
        barcodes = decode(frame_gray)
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            return barcode_data


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QGridLayout()
        self.folder_code = None
        # TODO: добавить количество камер и сделать динамический выбор
        # self.camera_widget1 = CameraWidget(2)  # Инициализация камеры под индексом 0
        self.camera_widget2 = CameraWidget(0)  # Инициализация камеры под индексом 4
        # self.camera_widget3 = CameraWidget(4)
        self.camera_widget4 = CameraWidget(3)

        self.take_photo_button = QPushButton("Take Photo")  # кнопка фотографирования
        self.take_photo_button.clicked.connect(self.take_photo)

        self.scan_button = QPushButton('Scan Barcode')
        self.scan_button.clicked.connect(self.read_barcode)

        self.code_label = QLabel("Barcode:")

        validator = QRegularExpressionValidator(QRegularExpression("^\d+$"))

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("штрих-код")
        self.line_edit.returnPressed.connect(self.return_pressed)
        self.line_edit.setValidator(validator)

        # self.layout.addWidget(self.camera_widget1.label, 0, 0)
        self.layout.addWidget(self.camera_widget2.label, 0, 1)
        # self.layout.addWidget(self.camera_widget3.label, 1, 0)
        self.layout.addWidget(self.camera_widget4.label, 1, 1)

        self.layout.addWidget(self.code_label, 4, 0, 1, 2, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.line_edit, 5, 0, 1, 2, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.take_photo_button, 2, 0, 1, 2, )
        self.layout.addWidget(self.scan_button, 3, 0, 1, 2)
        self.setLayout(self.layout)

    # метод, вызываемый нажатием кнопки "Take photo"
    def take_photo(self):
        if self.folder_code is not None:
            Path(f"Dataset/{self.folder_code}").mkdir(parents=True, exist_ok=True)
            for camera_widget in [self.camera_widget2, self.camera_widget4]:
                camera_widget.take_photo(self.folder_code)
        else:
            self.code_label.setText("Сначала простканируйте штрихкод товара")

    # метод, вызываемый нажатием кнопки "Scan Barcode"
    def read_barcode(self):
        # Выполняется поочередное считываение шрих-кодов с камер
        for camera_widget in [self.camera_widget1, self.camera_widget2]:
            code = camera_widget.read_barcode()
            self.folder_code = code
            self.code_label.setText("Barcode: " + str(code))

    def return_pressed(self):
        code = self.line_edit.text()
        self.folder_code = code
        self.line_edit.clear()
        self.code_label.setText("Barcode: " + str(code))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec())

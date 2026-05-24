from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

class TagWidget(QWidget):
    def __init__(self, tag_text, parent=None):
        super().__init__(parent)
        self.tag_text = tag_text
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Crear un widget que contiene el QLabel y el QPushButton
        self.label = QLabel(self.tag_text)
        self.label.setStyleSheet("background-color: lightgray; border-radius: 10px; padding: 0px; margin: 0px;")
        self.label.setFixedHeight(16)  # Fijar la altura del QLabel

        self.close_button = QPushButton("x")
        self.close_button.setStyleSheet("background-color: transparent; color: black; border: none; padding: 0px; margin: 0px;")
        self.close_button.setFixedSize(10, 10)  # Hacer el botón más pequeño y de tamaño fijo
        self.close_button.clicked.connect(self.delete_self)

        # Crear un layout interno para contener el QLabel y el QPushButton
        internal_layout = QHBoxLayout()
        internal_layout.addWidget(self.label)
        internal_layout.addWidget(self.close_button)
        internal_layout.setContentsMargins(0, 0, 0, 0)
        internal_layout.setSpacing(0)

        # Crear un widget interno que contendrá el QLabel y el QPushButton
        internal_widget = QWidget()
        internal_widget.setLayout(internal_layout)
        internal_widget.setStyleSheet("background-color: lightgray; border-radius: 10px; padding: 0px; margin: 0px;")
        internal_widget.setFixedHeight(20)  # Fijar la altura del widget interno

        layout.addWidget(internal_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def delete_self(self):
        self.setParent(None)
        self.deleteLater()

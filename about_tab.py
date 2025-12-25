from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import os

class AboutTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.info_layout = QVBoxLayout()

        self.info_layout.setContentsMargins(0, 10, 0, 0)
        self.info_layout.setSpacing(0)

        self.version_label = QLabel(
            "<b>GNU Mau</b>, the <i>Modular Application Utility</i>, is a cross-platform program (GNU Linux, Windows) <br>"
            "that helps us organize tasks, notes and credentials in projects. It is designed for backend and <br>"
            "DevOps developers, but it is an open-source utility that can be used by anyone."
        )
        self.version_label.setContentsMargins(10, 10, 0, 0)
        self.info_layout.addWidget(self.version_label)

        labels_data = [
            ("version:", "v0.0.7 Alpha"),
            ("license:", "GPL V3"),
            ("packaged:", "Ronal Forero"),
            ("translated:", "Ronal Forero"),
            ("tested:", "Kelly Gomez"),
            ("designer:", "Ronal Forero"),
            ("development by:", "Ronal Forero")
        ]

        for title, value in labels_data:
            lbl = QLabel(f"<b>{title}</b> {value}")
            lbl.setContentsMargins(10, 10, 0, 0)
            self.info_layout.addWidget(lbl)

        self.copyright_label = QLabel("<br>Copyright © 2024 Ronal Forero. Licensed under GPL v3.")
        self.copyright_label.setContentsMargins(10, 10, 0, 0)
        self.info_layout.addWidget(self.copyright_label)

        self.info_layout.addStretch()

        image_row_layout = QHBoxLayout()
        image_row_layout.addStretch() 
        
        self.image_label = QLabel()
        
        base_path = os.path.dirname(__file__) 
        image_path = os.path.join(base_path, "assets", "banner", "mau-alpha.png")
        
        pixmap = QPixmap(image_path)
        
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap.scaledToWidth(120, Qt.SmoothTransformation))
        else:
            print(f"DEBUG: No se encontró la imagen en: {image_path}")
            self.image_label.setText("[Imagen]")
            
        self.image_label.setContentsMargins(0, 0, 20, 20)
        image_row_layout.addWidget(self.image_label)

        self.info_layout.addLayout(image_row_layout)

        self.setLayout(self.info_layout)
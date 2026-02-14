from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from pacmanprogress import Pacman

class CustomProgressBar(QWidget):
    """
    A styled progress bar that abstracts the Pacman animation logic.
    Styled to match the user's restoration note.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_label = QLabel("")
        self.progress_label.setWordWrap(True)
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 11px;
                padding: 10px;
                border: 1px solid rgba(149, 165, 166, 0.2);
                border-radius: 5px;
                background-color: rgba(149, 165, 166, 0.05);
                margin-top: 5px;
            }
        """)
        self.layout.addWidget(self.progress_label)
        
        self.pacman = None
        self.hide() # Hidden by default until started

    def start(self, start=0, end=100, text="Progress", candy_count=35):
        self.show()
        self.pacman = Pacman(self.progress_label, start=start, end=end, width=35, text=text, candy_count=candy_count)
    
    def update_progress(self, value=1):
        if self.pacman:
            self.pacman.update(value)
            if self.pacman.step >= self.pacman.end:
                # Optional: Handle completion (e.g., hide after a delay)
                pass

    def set_text(self, text):
        self.progress_label.setText(text)

    def reset(self):
        self.progress_label.setText("")
        self.hide()

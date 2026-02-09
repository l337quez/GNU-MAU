from PySide6.QtWidgets import ( QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem)
from PySide6.QtCore import  Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt

class EmojiPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emoji Picker")
        self.setFixedSize(300, 400) 
        self.selected_emoji = None
        
        layout = QVBoxLayout(self)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 search emoji (ej: feliz, fuego)...")
        self.search_input.textChanged.connect(self.filter_emojis)
        layout.addWidget(self.search_input)
        
        self.list_widget = QListWidget()
        font = self.list_widget.font()
        font.setPointSize(12)
        self.list_widget.setFont(font)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)
        
        self.emoji_data = {
            "😀": "feliz happy sonrisa",
            "😂": "risa llorar joy lol",
            "😎": "cool gafas sol",
            "🤔": "pensar duda thinking",
            "👍": "bien like ok up",
            "👎": "mal dislike down",
            "🔥": "fuego fire hot",
            "✨": "estrellas magia spark",
            "❤️": "corazon amor love",
            "✅": "check listo bien",
            "❌": "x error mal",
            "⚠️": "warning alerta cuidado",
            "📅": "calendario fecha",
            "🚀": "cohete rocket",
            "💻": "pc ordenador laptop code",
            "📝": "nota escribir memo",
            "📌": "pin fijar",
            "🔗": "link enlace cadena",
            "🐍": "python serpiente"
        }
        
        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for emoji, keywords in self.emoji_data.items():
            item = QListWidgetItem(f"{emoji}   {keywords}")
            item.setData(Qt.UserRole, emoji) 
            self.list_widget.addItem(item)

    def filter_emojis(self, text):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def on_item_clicked(self, item):
        self.selected_emoji = item.data(Qt.UserRole)
        self.accept() 
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QAbstractItemView, QMessageBox
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QTextCursor
from bson.objectid import ObjectId
from todo_text_editor import TodoTextEditor
from emoji_picker import EmojiPicker
class ProjectTodoTab(QWidget):
    def __init__(self, main_window, project_id):
        super().__init__()
        self.main_window = main_window
        self.project_id = project_id
        self.todos_collection = self.main_window.db.todos
        self.current_todo_id = None

        self.init_ui()
        self.load_todos()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(20)

        self.left_panel = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel_layout.setSpacing(5)

        self.todo_list_widget = QListWidget()
        self.todo_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.todo_list_widget.itemClicked.connect(self.select_todo_item)
        
        self.add_button = QPushButton("➕ New TODO")
        self.add_button.clicked.connect(self.create_new_todo)
        
        # Botón Eliminar (Nuevo)
        self.delete_button = QPushButton("🗑️ Delete TODO")
        self.delete_button.setStyleSheet("color: #ff4d4d;") # Opcional: rojo para advertir
        self.delete_button.clicked.connect(self.delete_current_todo)

        self.left_panel_layout.addWidget(self.todo_list_widget)
        self.left_panel_layout.addWidget(self.add_button)
        self.left_panel_layout.addWidget(self.delete_button)

        # --- Panel Derecho ---
        self.right_panel = QWidget()
        self.right_panel_layout = QVBoxLayout(self.right_panel)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("List title...")
        self.title_input.textChanged.connect(self.start_save_timer)

        self.toolbar_layout = QHBoxLayout()
        self.checkbox_button = QPushButton("☐ Insert task")
        self.checkbox_button.clicked.connect(self.insert_checkbox_at_cursor)
        self.toolbar_layout.addWidget(self.checkbox_button)

        self.emoji_button = QPushButton("😊")
        self.emoji_button.setFixedWidth(40) 
        self.emoji_button.clicked.connect(self.open_emoji_picker)
        self.toolbar_layout.addWidget(self.emoji_button)

        self.clean_button = QPushButton("🧹 Clean Format")
        self.clean_button.setToolTip("Elimina colores de fondo y estilos raros")
        self.clean_button.clicked.connect(self.clean_text_format)
        self.toolbar_layout.addWidget(self.clean_button)
        
        self.toolbar_layout.addStretch()

        self.toolbar_layout.addStretch()

        self.text_editor = TodoTextEditor()
        self.text_editor.textChanged.connect(self.start_save_timer)

        self.right_panel_layout.addWidget(self.title_input)
        self.right_panel_layout.addLayout(self.toolbar_layout)
        self.right_panel_layout.addWidget(self.text_editor)

        self.main_layout.addWidget(self.left_panel, 1)
        self.main_layout.addWidget(self.right_panel, 2)

        self.save_timer = QTimer(self)
        self.save_timer.setInterval(1000)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_current_todo)

    def delete_current_todo(self):
        if not self.current_todo_id:
            return

        # Confirmación de usuario
        reply = QMessageBox.question(
            self, 'Remove TODO',
            "Are you sure you want to remove this TODO?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.todos_collection.delete_one({"_id": ObjectId(self.current_todo_id)})
            
            # Clean vars
            self.current_todo_id = None
            self.title_input.clear()
            self.text_editor.clear()
            
            self.load_todos()

    def load_todos(self):
        self.title_input.blockSignals(True)
        self.text_editor.blockSignals(True)
        self.todo_list_widget.clear()
        
        todos = self.todos_collection.find({"project_id": str(self.project_id)})
        for todo in todos:
            item = QListWidgetItem(todo["title"])
            item.setData(Qt.UserRole, str(todo["_id"]))
            self.todo_list_widget.addItem(item)
        
        self.title_input.blockSignals(False)
        self.text_editor.blockSignals(False)

        if self.todo_list_widget.count() > 0:
            self.todo_list_widget.setCurrentRow(0)
            self.select_todo_item(self.todo_list_widget.currentItem())
        else:
            self.current_todo_id = None

    def create_new_todo(self):
        self.save_current_todo()
        new_todo = {
            "title": "New TODO",
            "content": "☐ My first task",
            "project_id": str(self.project_id)
        }
        res = self.todos_collection.insert_one(new_todo)
        self.load_todos()
        
        for i in range(self.todo_list_widget.count()):
            if self.todo_list_widget.item(i).data(Qt.UserRole) == str(res.inserted_id):
                self.todo_list_widget.setCurrentRow(i)
                self.select_todo_item(self.todo_list_widget.item(i))
                break

    def select_todo_item(self, item):
        if not item: return
        self.save_current_todo()
        self.current_todo_id = item.data(Qt.UserRole)
        data = self.todos_collection.find_one({"_id": ObjectId(self.current_todo_id)})
        
        if data:
            self.title_input.blockSignals(True)
            self.text_editor.blockSignals(True)
            self.title_input.setText(data.get("title", ""))
            self.text_editor.setPlainText(data.get("content", ""))
            self.title_input.blockSignals(False)
            self.text_editor.blockSignals(False)

    def insert_checkbox_at_cursor(self):
        cursor = self.text_editor.textCursor()
        if not cursor.atBlockStart():
            cursor.insertBlock()
        cursor.insertText("☐ ")
        self.text_editor.setFocus()

    def start_save_timer(self):
        if self.current_todo_id:
            self.save_timer.start()

    def save_current_todo(self):
            if not self.current_todo_id: return
            self.save_timer.stop()
            
            title = self.title_input.text()
            # toPlainText() captura todos los caracteres Unicode (incluyendo ☐ y ☑)
            content = self.text_editor.toPlainText()
            
            self.todos_collection.update_one(
                {"_id": ObjectId(self.current_todo_id)},
                {"$set": {
                    "title": title, 
                    "content": content,
                    "project_id": str(self.project_id) # Aseguramos consistencia
                }}
            )
            
            curr = self.todo_list_widget.currentItem()
            if curr: curr.setText(title)

    def update_project_id(self, new_project_id):
        if self.current_todo_id:
            self.save_current_todo()
        self.project_id = new_project_id
        self.current_todo_id = None 
        self.load_todos()
    
    def open_emoji_picker(self):
        dialog = EmojiPicker(self)
        
        if dialog.exec(): 
            if dialog.selected_emoji:
                cursor = self.text_editor.textCursor()
                cursor.insertText(dialog.selected_emoji)
                self.text_editor.setFocus()
    
    def clean_text_format(self):
        """
        Remove rich text formatting (background colors, fonts)
        and leave only plain text.
        """
        cursor = self.text_editor.textCursor()
        
        if not cursor.hasSelection():
            cursor.select(QTextCursor.Document)
        
        if cursor.hasSelection():
            text_puro = cursor.selectedText().replace('\u2029', '\n')
            
            from PySide6.QtGui import QTextCharFormat
            formato_limpio = QTextCharFormat() 
            cursor.setCharFormat(formato_limpio)
            cursor.insertText(text_puro)
            self.text_editor.setFocus()
            self.start_save_timer()
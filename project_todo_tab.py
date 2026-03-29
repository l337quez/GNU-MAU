# Pyside imports
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QAbstractItemView, QMessageBox,
    QApplication, QLabel
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont
# Other imports
from bson.objectid import ObjectId
# MAU imports
from todo_text_editor import TodoTextEditor
from emoji_picker import EmojiPicker
from utils import clean_text_format

class ProjectTodoTab(QWidget):
    def __init__(self, main_window, project_id):
        super().__init__()
        self.main_window = main_window
        self.project_id = project_id
        self.todos_collection = self.main_window.db.todos
        self.current_todo_id = None
        self.current_todo_item = None  # Rastreo explícito del item seleccionado

        self.init_ui()
        self.load_todos()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(5)

        # Confirmation Widget (Inline - Top Level)
        self.confirmation_widget = QWidget()
        self.confirmation_widget.setVisible(False)
        self.confirm_layout = QVBoxLayout(self.confirmation_widget)
        self.confirm_layout.setContentsMargins(0, 0, 0, 10)
        self.confirm_layout.setSpacing(5)

        self.confirm_label = QLabel("Delete this TODO?")
        self.confirm_label.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 14px;")
        self.confirm_layout.addWidget(self.confirm_label)

        self.confirm_btns_layout = QHBoxLayout()
        self.confirm_yes_btn = QPushButton("Yes, Delete")
        self.confirm_yes_btn.setStyleSheet("background-color: #ff4d4d; color: white; padding: 5px 15px;")
        self.confirm_yes_btn.clicked.connect(self.confirm_deletion)
        
        self.confirm_no_btn = QPushButton("Cancel")
        self.confirm_no_btn.clicked.connect(self.cancel_deletion)
        
        self.confirm_btns_layout.addWidget(self.confirm_yes_btn)
        self.confirm_btns_layout.addWidget(self.confirm_no_btn)
        self.confirm_btns_layout.addStretch()
        self.confirm_layout.addLayout(self.confirm_btns_layout)

        self.main_layout.addWidget(self.confirmation_widget)

        # Container for panels
        self.panels_layout = QHBoxLayout()
        self.panels_layout.setSpacing(20)
        self.main_layout.addLayout(self.panels_layout)

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
        self.emoji_button.setFixedWidth(35) 
        self.emoji_button.clicked.connect(self.open_emoji_picker)
        self.toolbar_layout.addWidget(self.emoji_button)

        self.clean_button = QPushButton("🧹")
        self.clean_button.setFixedWidth(35) 
        self.clean_button.setToolTip("Clean Format")
        # self.clean_button.clicked.connect(self.clean_text_format)
        self.clean_button.clicked.connect(lambda: clean_text_format(self.text_editor, self.save_current_todo))
        self.toolbar_layout.addWidget(self.clean_button)


        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedWidth(35)
        self.bold_btn.clicked.connect(self.toggle_bold) 
        self.toolbar_layout.addWidget(self.bold_btn)

        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedWidth(35)
        self.copy_btn.setToolTip("Copy TODO List")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.toolbar_layout.addWidget(self.copy_btn)

        
        self.toolbar_layout.addStretch()

        self.toolbar_layout.addStretch()

        self.text_editor = TodoTextEditor()
        self.text_editor.textChanged.connect(self.start_save_timer)

        self.right_panel_layout.addWidget(self.title_input)
        self.right_panel_layout.addLayout(self.toolbar_layout)
        self.right_panel_layout.addWidget(self.text_editor)

        self.panels_layout.addWidget(self.left_panel, 1)
        self.panels_layout.addWidget(self.right_panel, 2)

        self.save_timer = QTimer(self)
        self.save_timer.setInterval(1000)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_current_todo)

    def delete_current_todo(self):
        if not self.current_todo_id:
            return
        
        title = self.title_input.text()
        self.confirm_label.setText(f"Delete '{title}'?")
        self.confirmation_widget.setVisible(True)
        self.delete_button.setEnabled(False)
        self.add_button.setEnabled(False)

    def confirm_deletion(self):
        if self.current_todo_id:
            self.todos_collection.delete_one({"_id": ObjectId(self.current_todo_id)})
            
            # Clean vars
            self.current_todo_id = None
            self.current_todo_item = None
            self.title_input.clear()
            self.text_editor.clear()
            
            self.load_todos()
        self.cancel_deletion()

    def cancel_deletion(self):
        self.confirmation_widget.setVisible(False)
        self.delete_button.setEnabled(True)
        self.add_button.setEnabled(True)

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
        # Guardar el item ANTERIOR con referencia explícita antes de cambiar el ID
        # (currentItem() ya devuelve el nuevo item cuando Qt dispara itemClicked)
        self.save_current_todo()
        self.current_todo_id = item.data(Qt.UserRole)
        self.current_todo_item = item
        data = self.todos_collection.find_one({"_id": ObjectId(self.current_todo_id)})
        
        if data:
            self.title_input.blockSignals(True)
            self.text_editor.blockSignals(True)
            self.title_input.setText(data.get("title", ""))
            # self.text_editor.setPlainText(data.get("content", ""))
            self.text_editor.setMarkdown(data.get("content", ""))
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

    def save_current_todo(self, target_item=None):
            if not self.current_todo_id: return
            self.save_timer.stop()
            
            title = self.title_input.text()
            content = self.text_editor.toMarkdown()

            self.todos_collection.update_one(
                {"_id": ObjectId(self.current_todo_id)},
                {"$set": {
                    "title": title, 
                    "content": content,
                    "project_id": str(self.project_id)
                }}
            )
            
            # Siempre usar el item rastreado explícitamente, nunca currentItem()
            item_to_update = self.current_todo_item
            if item_to_update:
                try:
                    item_to_update.setText(title)
                except RuntimeError:
                    self.current_todo_item = None

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
    


    def toggle_bold(self):
        cursor = self.text_editor.textCursor()
        
        if not cursor.hasSelection():
            fmt = self.text_editor.currentCharFormat()
            new_weight = QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal
            fmt.setFontWeight(new_weight)
            self.text_editor.setCurrentCharFormat(fmt)
        else:
            fmt = cursor.charFormat()
            new_fmt = QTextCharFormat()
            new_fmt.setFontWeight(QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.mergeCharFormat(new_fmt)
        
        self.text_editor.setFocus()
        self.start_save_timer()

    def copy_to_clipboard(self):
        content = self.text_editor.toPlainText()
        if content:
            QApplication.clipboard().setText(content)
            self.main_window.statusBar().showMessage("TODO list copied to clipboard!", 3000)
        else:
            self.main_window.statusBar().showMessage("Nothing to copy.", 3000)
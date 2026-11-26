# Pyside imports
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QAbstractItemView, QMessageBox,
    QApplication, QLabel, QSplitter, QStackedWidget
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont
# Other imports
from bson.objectid import ObjectId
# MAU imports
from todo_text_editor import TodoTextEditor
from emoji_picker import EmojiPicker
from utils import clean_text_format, format_project_header
from i18n import tr
from kanban_view import KanbanBoardWidget

class ProjectTodoTab(QWidget):
    def __init__(self, main_window, project_id):
        super().__init__()
        self.main_window = main_window
        self.project_id = project_id
        self.todos_collection = self.main_window.db.todos
        self.current_project_name = ""
        self.current_todo_id = None
        self.current_todo_item = None  # Rastreo explícito del item seleccionado

        self.init_ui()
        self.load_todos()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(5)

        # Project contextual header
        self.project_header_label = QLabel()
        self.project_header_label.setStyleSheet("margin-bottom: 4px;")
        self.main_layout.addWidget(self.project_header_label)

        # Confirmation Widget (Inline - Top Level)
        self.confirmation_widget = QWidget()
        self.confirmation_widget.setVisible(False)
        self.confirm_layout = QVBoxLayout(self.confirmation_widget)
        self.confirm_layout.setContentsMargins(0, 0, 0, 10)
        self.confirm_layout.setSpacing(5)

        self.confirm_label = QLabel(tr("delete_todo_confirm"))
        self.confirm_label.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 14px;")
        self.confirm_layout.addWidget(self.confirm_label)

        self.confirm_btns_layout = QHBoxLayout()
        self.confirm_yes_btn = QPushButton(tr("btn_yes_delete"))
        self.confirm_yes_btn.setStyleSheet("background-color: #ff4d4d; color: white; padding: 5px 15px;")
        self.confirm_yes_btn.clicked.connect(self.confirm_deletion)
        
        self.confirm_no_btn = QPushButton(tr("btn_cancel"))
        self.confirm_no_btn.clicked.connect(self.cancel_deletion)
        
        self.confirm_btns_layout.addWidget(self.confirm_yes_btn)
        self.confirm_btns_layout.addWidget(self.confirm_no_btn)
        self.confirm_btns_layout.addStretch()
        self.confirm_layout.addLayout(self.confirm_btns_layout)

        self.main_layout.addWidget(self.confirmation_widget)

        # Top Control Bar (Search + Add Column + View Switcher)
        self.top_control_layout = QHBoxLayout()
        self.top_control_layout.setContentsMargins(0, 0, 0, 6)
        self.top_control_layout.setSpacing(10)

        # Buscador de tareas (hereda el tema activo)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_tasks_placeholder", "🔍 Search tasks..."))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        self.top_control_layout.addWidget(self.search_input, stretch=1)

        # Botón Nueva Tarea (funciona en ambas vistas)
        self.top_add_task_btn = QPushButton(tr("new_list", "➕ New Task"))
        self.top_add_task_btn.setCursor(Qt.PointingHandCursor)
        self.top_add_task_btn.setFixedHeight(30)
        self.top_add_task_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 128, 128, 0.12);
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.22);
            }
        """)
        self.top_add_task_btn.clicked.connect(self.top_add_task_clicked)
        self.top_control_layout.addWidget(self.top_add_task_btn)

        # Botón Agregar Columna (activo en vista Board)
        self.add_column_btn = QPushButton(tr("add_column", "➕ Add Column"))
        self.add_column_btn.setCursor(Qt.PointingHandCursor)
        self.add_column_btn.setFixedHeight(30)
        self.add_column_btn.clicked.connect(self.add_column_clicked)
        self.top_control_layout.addWidget(self.add_column_btn)

        # Selector segmentado de vista: [ 📋 List ] [ 📊 Board ] (cambio en 1 clic sin desplazamientos)
        self.btn_view_list = QPushButton(tr("view_list", "📋 List"))
        self.btn_view_list.setCursor(Qt.PointingHandCursor)
        self.btn_view_list.setFixedHeight(30)
        self.btn_view_list.clicked.connect(self.switch_to_list_view)

        self.btn_view_board = QPushButton(tr("view_board", "📊 Board"))
        self.btn_view_board.setCursor(Qt.PointingHandCursor)
        self.btn_view_board.setFixedHeight(30)
        self.btn_view_board.clicked.connect(self.switch_to_board_view)

        self.update_view_buttons(0)

        self.top_control_layout.addWidget(self.btn_view_list)
        self.top_control_layout.addWidget(self.btn_view_board)

        self.main_layout.addLayout(self.top_control_layout)

        # QStackedWidget para alternar entre vista Clásica y Kanban
        self.view_stack = QStackedWidget()
        self.main_layout.addWidget(self.view_stack)

        # Divisor redimensionable (QSplitter) para vista clásica
        self.splitter = QSplitter(Qt.Horizontal)

        self.left_panel = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel_layout.setSpacing(5)

        self.todo_list_widget = QListWidget()
        self.todo_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.todo_list_widget.itemClicked.connect(self.select_todo_item)
        
        self.add_button = QPushButton(tr("new_list"))
        self.add_button.clicked.connect(self.create_new_todo)

        self.refresh_button = QPushButton(tr("refresh"))
        self.refresh_button.clicked.connect(self.load_todos)
        
        # Botón Eliminar
        self.delete_button = QPushButton(tr("delete_list"))
        self.delete_button.setStyleSheet("color: #ff4d4d;")
        self.delete_button.clicked.connect(self.delete_current_todo)

        self.left_panel_layout.addWidget(self.todo_list_widget)
        self.left_panel_layout.addWidget(self.add_button)
        self.left_panel_layout.addWidget(self.refresh_button)
        self.left_panel_layout.addWidget(self.delete_button)

        # --- Panel Derecho ---
        self.right_panel = QWidget()
        self.right_panel_layout = QVBoxLayout(self.right_panel)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(tr("list_title_placeholder"))
        self.title_input.textChanged.connect(self.start_save_timer)

        self.toolbar_layout = QHBoxLayout()
        self.checkbox_button = QPushButton(tr("insert_task"))
        self.checkbox_button.clicked.connect(self.insert_checkbox_at_cursor)
        self.toolbar_layout.addWidget(self.checkbox_button)

        self.emoji_button = QPushButton("😊")
        self.emoji_button.setFixedWidth(35) 
        self.emoji_button.clicked.connect(self.open_emoji_picker)
        self.toolbar_layout.addWidget(self.emoji_button)

        self.clean_button = QPushButton("🧹")
        self.clean_button.setFixedWidth(35) 
        self.clean_button.setToolTip(tr("clean_format"))
        self.clean_button.clicked.connect(lambda: clean_text_format(self.text_editor, self.save_current_todo))
        self.toolbar_layout.addWidget(self.clean_button)

        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedWidth(35)
        self.bold_btn.setToolTip(tr("bold"))
        self.bold_btn.clicked.connect(self.toggle_bold) 
        self.toolbar_layout.addWidget(self.bold_btn)

        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedWidth(35)
        self.copy_btn.setToolTip(tr("copy_tasks"))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.toolbar_layout.addWidget(self.copy_btn)

        self.toolbar_layout.addStretch()

        self.text_editor = TodoTextEditor()
        self.text_editor.textChanged.connect(self.start_save_timer)

        self.right_panel_layout.addWidget(self.title_input)
        self.right_panel_layout.addLayout(self.toolbar_layout)
        self.right_panel_layout.addWidget(self.text_editor)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.view_stack.addWidget(self.splitter)

        # Tablero Kanban con cards arrastrables estilo Jira/Trello
        self.kanban_board = KanbanBoardWidget(self.main_window, self.project_id)
        self.kanban_board.card_updated.connect(self.on_kanban_updated)
        self.view_stack.addWidget(self.kanban_board)

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

        if hasattr(self, "search_input") and self.search_input.text():
            self.filter_classic_todos(self.search_input.text())

        if self.todo_list_widget.count() > 0:
            self.title_input.setEnabled(True)
            self.text_editor.setEnabled(True)
            self.todo_list_widget.setCurrentRow(0)
            self.select_todo_item(self.todo_list_widget.currentItem())
        else:
            self.current_todo_id = None
            self.title_input.clear()
            self.text_editor.clear()
            self.title_input.setEnabled(False)
            self.text_editor.setEnabled(False)
            self.title_input.setPlaceholderText(tr("no_tasks_placeholder"))

    def top_add_task_clicked(self):
        if self.view_stack.currentIndex() == 1:
            first_col = self.kanban_board.columns[0] if self.kanban_board.columns else "To Do"
            self.kanban_board.add_card_to_column(first_col)
        else:
            self.create_new_todo()

    def create_new_todo(self):
        self.save_current_todo()
        first_col = self.kanban_board.columns[0] if hasattr(self, "kanban_board") and self.kanban_board.columns else "To Do"
        new_todo = {
            "title": tr("default_new_todo_title", "New List"),
            "content": tr("default_new_task", "☐ My first task"),
            "project_id": str(self.project_id),
            "status": first_col,
            "column": first_col
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
        self.title_input.setEnabled(True)
        self.text_editor.setEnabled(True)
        self.save_current_todo()
        self.current_todo_id = item.data(Qt.UserRole)
        self.current_todo_item = item
        data = self.todos_collection.find_one({"_id": ObjectId(self.current_todo_id)})
        
        if data:
            self.title_input.blockSignals(True)
            self.text_editor.blockSignals(True)
            self.title_input.setText(data.get("title", ""))
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
            
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(tr("status_saved"), 2000)
            
            # Siempre usar el item rastreado explícitamente, nunca currentItem()
            item_to_update = self.current_todo_item
            if item_to_update:
                try:
                    item_to_update.setText(title)
                except RuntimeError:
                    self.current_todo_item = None

    def update_view_buttons(self, active_idx):
        active_style = """
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #2563eb;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: rgba(128, 128, 128, 0.12);
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.22);
            }
        """
        if active_idx == 0:
            self.btn_view_list.setStyleSheet(active_style)
            self.btn_view_board.setStyleSheet(inactive_style)
            self.add_column_btn.setEnabled(False)
            self.add_column_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px dashed rgba(128, 128, 128, 0.25);
                    color: rgba(128, 128, 128, 0.45);
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 12px;
                }
            """)
        else:
            self.btn_view_list.setStyleSheet(inactive_style)
            self.btn_view_board.setStyleSheet(active_style)
            self.add_column_btn.setEnabled(True)
            self.add_column_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(128, 128, 128, 0.12);
                    border: 1px solid rgba(128, 128, 128, 0.25);
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.22);
                }
            """)

    def switch_to_list_view(self):
        """Cambia a la vista de lista clásica en 1 solo clic garantizado."""
        if self.view_stack.currentIndex() != 0:
            self.view_stack.setCurrentIndex(0)
            self.update_view_buttons(0)
            self.load_todos()
            if self.search_input.text():
                self.filter_classic_todos(self.search_input.text())

    def switch_to_board_view(self):
        """Cambia a la vista de tablero Kanban en 1 solo clic garantizado."""
        if self.view_stack.currentIndex() != 1:
            if self.current_todo_id:
                self.save_current_todo()
            self.view_stack.setCurrentIndex(1)
            self.update_view_buttons(1)
            self.kanban_board.refresh_board()
            if self.search_input.text():
                self.kanban_board.filter_cards(self.search_input.text())

    def toggle_view_mode(self):
        if self.view_stack.currentIndex() == 0:
            self.switch_to_board_view()
        else:
            self.switch_to_list_view()

    def on_search_changed(self, text):
        """Filtra en tiempo real según la vista activa."""
        if self.view_stack.currentIndex() == 1:
            self.kanban_board.filter_cards(text)
        else:
            self.filter_classic_todos(text)

    def filter_classic_todos(self, query):
        query = query.strip().lower()
        for i in range(self.todo_list_widget.count()):
            item = self.todo_list_widget.item(i)
            matches = query in (item.text() or "").lower()
            item.setHidden(not matches)

    def add_column_clicked(self):
        if self.view_stack.currentIndex() != 1:
            self.toggle_view_mode()
        self.kanban_board.prompt_add_column()

    def on_kanban_updated(self):
        # Cuando se actualizan tarjetas en Kanban, sincronizar lista clásica si está cargada
        pass

    def update_project_id(self, new_project_id):
        if self.current_todo_id:
            self.save_current_todo()
        self.project_id = new_project_id
        self.current_todo_id = None
        self.kanban_board.project_id = new_project_id
        if self.view_stack.currentIndex() == 1:
            self.kanban_board.refresh_board()
        else:
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
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(tr("copied_to_clipboard"), 2500)
            elif hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(tr("copied_to_clipboard"), 2500)
        else:
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(tr("nothing_to_copy"), 2500)
            elif hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(tr("nothing_to_copy"), 2500)

    def update_project_name(self, name):
        """Actualiza el encabezado contextual con el nombre del proyecto."""
        self.current_project_name = name or ""
        self.project_header_label.setText(format_project_header(self.current_project_name))

    def retranslate_ui(self):
        if getattr(self, "current_project_name", ""):
            self.project_header_label.setText(format_project_header(self.current_project_name))
        self.confirm_label.setText(tr("delete_todo_confirm"))
        self.confirm_yes_btn.setText(tr("btn_yes_delete"))
        self.confirm_no_btn.setText(tr("btn_cancel"))
        self.add_button.setText(tr("new_list"))
        self.refresh_button.setText(tr("refresh"))
        self.delete_button.setText(tr("delete_list"))
        self.checkbox_button.setText(tr("insert_task"))
        self.clean_button.setToolTip(tr("clean_format"))
        self.bold_btn.setToolTip(tr("bold"))
        self.copy_btn.setToolTip(tr("copy_tasks"))
        self.top_add_task_btn.setText(tr("new_list", "➕ New Task"))
        self.search_input.setPlaceholderText(tr("search_tasks_placeholder", "🔍 Search tasks..."))
        self.add_column_btn.setText(tr("add_column", "➕ Add Column"))
        self.btn_view_list.setText(tr("view_list", "📋 List"))
        self.btn_view_board.setText(tr("view_board", "📊 Board"))
        if self.todo_list_widget.count() == 0:
            self.title_input.setPlaceholderText(tr("no_tasks_placeholder"))
        else:
            self.title_input.setPlaceholderText(tr("list_title_placeholder"))
        if hasattr(self, "kanban_board") and self.view_stack.currentIndex() == 1:
            self.kanban_board.refresh_board()
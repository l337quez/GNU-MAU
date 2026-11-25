"""
GNU Mau - Kanban Board View module.
Provides a Trello / Jira style board with draggable cards, customizable columns,
search filtering, and theme-adaptive card rendering.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QListWidget,
    QListWidgetItem, QLabel, QPushButton, QFrame, QAbstractItemView,
    QStyledItemDelegate, QMenu, QInputDialog, QMessageBox, QDialog,
    QLineEdit, QComboBox, QApplication, QStyle
)
from PySide6.QtCore import Qt, QSize, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPalette
from bson.objectid import ObjectId

from todo_text_editor import TodoTextEditor
from emoji_picker import EmojiPicker
from utils import clean_text_format
from i18n import tr


def get_default_columns():
    return [
        tr("col_todo", "To Do"),
        tr("col_in_progress", "In Progress"),
        tr("col_done", "Done")
    ]


def extract_card_metadata(content: str):
    """
    Extracts snippet and checkbox progress from markdown content.
    Returns: (snippet_text, badge_text, is_all_done)
    """
    if not content:
        return ("", "", False)
    
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    snippet = ""
    total_checks = 0
    done_checks = 0

    for line in lines:
        if line.startswith("☐") or line.startswith("[ ]") or line.startswith("- [ ]"):
            total_checks += 1
            if not snippet:
                snippet = line.lstrip("☐-[] ").strip()
        elif line.startswith("☑") or line.startswith("[x]") or line.startswith("- [x]"):
            total_checks += 1
            done_checks += 1
            if not snippet:
                snippet = line.lstrip("☑-[]xX ").strip()
        elif not snippet:
            snippet = line

    if len(snippet) > 42:
        snippet = snippet[:40] + "..."

    badge = ""
    is_all_done = False
    if total_checks > 0:
        badge = f"☑ {done_checks}/{total_checks}"
        is_all_done = (done_checks == total_checks)

    return (snippet, badge, is_all_done)


class KanbanCardDelegate(QStyledItemDelegate):
    """
    Custom delegate rendering items as modern Trello / Jira style cards,
    adapting to light and dark themes.
    """
    def sizeHint(self, option, index):
        badge = index.data(Qt.UserRole + 2)
        height = 80 if badge else 66
        width = option.rect.width() if option and hasattr(option, "rect") and option.rect.width() > 0 else 240
        return QSize(width, height)

    def paint(self, painter, option, index):
        try:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            margin_x = 6
            margin_y = 4
            card_rect = option.rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)

            is_selected = bool(option.state & QStyle.State_Selected)
            is_hover = bool(option.state & QStyle.State_MouseOver)

            # Detect theme brightness from palette
            pal = option.palette
            win_color = pal.window().color()
            lum = (win_color.red() * 0.299 + win_color.green() * 0.587 + win_color.blue() * 0.114)
            is_dark = lum < 128

            if is_dark:
                # Dark theme styling
                bg_color = QColor("#282c34") if win_color.name() == "#1e1e1e" else pal.base().color()
                if bg_color == win_color:
                    bg_color = win_color.lighter(130)
                border_color = pal.highlight().color() if is_selected else (QColor("#525866") if is_hover else QColor("#3a3f4b"))
                title_color = QColor("#f3f4f6")
                snip_color = QColor("#9ca3af")
                badge_bg = QColor("#065f46") if index.data(Qt.UserRole + 3) else QColor("#374151")
                badge_text = QColor("#34d399") if index.data(Qt.UserRole + 3) else QColor("#d1d5db")
            else:
                # Light theme styling
                bg_color = QColor("#ffffff")
                border_color = pal.highlight().color() if is_selected else (QColor("#94a3b8") if is_hover else QColor("#e2e8f0"))
                title_color = QColor("#0f172a")
                snip_color = QColor("#64748b")
                badge_bg = QColor("#dcfce7") if index.data(Qt.UserRole + 3) else QColor("#f1f5f9")
                badge_text = QColor("#15803d") if index.data(Qt.UserRole + 3) else QColor("#475569")

            border_w = 1.6 if is_selected else (1.2 if is_hover else 1.0)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(border_color, border_w))
            painter.drawRoundedRect(card_rect, 7, 7)

            # Title
            title = index.data(Qt.DisplayRole) or ""
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(10)
            painter.setFont(title_font)
            painter.setPen(title_color)
            title_rect = QRect(card_rect.left() + 10, card_rect.top() + 8, card_rect.width() - 20, 20)
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, title)

            # Snippet / preview
            snippet = index.data(Qt.UserRole + 1) or ""
            snip_font = QFont()
            snip_font.setPointSize(9)
            painter.setFont(snip_font)
            painter.setPen(snip_color)
            snip_rect = QRect(card_rect.left() + 10, card_rect.top() + 28, card_rect.width() - 20, 18)
            painter.drawText(snip_rect, Qt.AlignLeft | Qt.AlignVCenter, snippet)

            # Checkbox progress badge
            badge = index.data(Qt.UserRole + 2) or ""
            if badge:
                badge_font = QFont()
                badge_font.setPointSize(8)
                badge_font.setBold(True)
                painter.setFont(badge_font)
                badge_rect = QRect(card_rect.left() + 10, card_rect.top() + 48, 68, 18)
                painter.setBrush(QBrush(badge_bg))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(badge_rect, 4, 4)
                painter.setPen(badge_text)
                painter.drawText(badge_rect, Qt.AlignCenter, badge)

            painter.restore()
        except Exception as e:
            print(f"KanbanCardDelegate paint exception: {e}")
            super().paint(painter, option, index)


class KanbanListWidget(QListWidget):
    """
    List widget representing cards inside a column, with full drag & drop support.
    """
    def __init__(self, column_widget):
        super().__init__()
        self.column_widget = column_widget
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setItemDelegate(KanbanCardDelegate(self))
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSpacing(2)
        self.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
            }
        """)

    def mimeData(self, items):
        mime = super().mimeData(items)
        if items:
            mime.setText(str(items[0].data(Qt.UserRole) or ""))
        return mime

    def dropEvent(self, event):
        todo_id = event.mimeData().text()
        super().dropEvent(event)
        if todo_id:
            self.column_widget.board.on_card_dropped(todo_id, self.column_widget.column_name)


class KanbanCardDialog(QDialog):
    """
    Dialog to view and edit card details (Title, Column, Markdown content, Delete).
    """
    def __init__(self, board, todo_data, columns, parent=None):
        super().__init__(parent)
        self.board = board
        self.todo_data = todo_data
        self.columns = columns
        self.todo_id = str(todo_data.get("_id"))
        self.deleted = False

        self.setWindowTitle(tr("card_detail_title", "Edit Task"))
        self.resize(650, 520)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # Header: Title & Column selector
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setText(self.todo_data.get("title", ""))
        self.title_input.setPlaceholderText(tr("list_title_placeholder", "Title..."))
        self.title_input.setStyleSheet("font-size: 15px; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        header_layout.addWidget(self.title_input, stretch=3)

        col_layout = QHBoxLayout()
        col_label = QLabel(tr("column_label", "Column:"))
        col_label.setStyleSheet("font-weight: 500;")
        self.col_combo = QComboBox()
        for c in self.columns:
            self.col_combo.addItem(c)
        current_status = self.todo_data.get("status") or self.todo_data.get("column") or self.columns[0]
        idx = self.col_combo.findText(current_status)
        if idx >= 0:
            self.col_combo.setCurrentIndex(idx)
        self.col_combo.setStyleSheet("padding: 5px 10px; border-radius: 6px;")
        col_layout.addWidget(col_label)
        col_layout.addWidget(self.col_combo)
        header_layout.addLayout(col_layout, stretch=2)

        layout.addLayout(header_layout)

        # Toolbar for editor
        tb_layout = QHBoxLayout()
        self.btn_insert_task = QPushButton(tr("insert_task", "☐ Insert task"))
        self.btn_insert_task.clicked.connect(self.insert_checkbox)
        tb_layout.addWidget(self.btn_insert_task)

        self.btn_emoji = QPushButton("😊")
        self.btn_emoji.setFixedWidth(35)
        self.btn_emoji.clicked.connect(self.open_emoji)
        tb_layout.addWidget(self.btn_emoji)

        self.btn_clean = QPushButton("🧹")
        self.btn_clean.setFixedWidth(35)
        self.btn_clean.setToolTip(tr("clean_format", "Clean format"))
        self.btn_clean.clicked.connect(lambda: clean_text_format(self.editor, lambda: None))
        tb_layout.addWidget(self.btn_clean)

        tb_layout.addStretch()
        layout.addLayout(tb_layout)

        # Markdown Editor
        self.editor = TodoTextEditor()
        self.editor.setMarkdown(self.todo_data.get("content", ""))
        layout.addWidget(self.editor)

        # Footer actions
        footer = QHBoxLayout()
        self.btn_delete = QPushButton(tr("delete_list", "🗑️ Delete Task"))
        self.btn_delete.setStyleSheet("color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); padding: 6px 14px; border-radius: 6px;")
        self.btn_delete.clicked.connect(self.delete_card)
        footer.addWidget(self.btn_delete)

        footer.addStretch()

        self.btn_cancel = QPushButton(tr("btn_cancel", "Cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(tr("btn_save", "💾 Save"))
        self.btn_save.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 6px 18px; border-radius: 6px;")
        self.btn_save.clicked.connect(self.save_card)
        footer.addWidget(self.btn_save)

        layout.addLayout(footer)

    def insert_checkbox(self):
        cursor = self.editor.textCursor()
        if not cursor.atBlockStart():
            cursor.insertBlock()
        cursor.insertText("☐ ")
        self.editor.setFocus()

    def open_emoji(self):
        picker = EmojiPicker(self)
        if picker.exec() and picker.selected_emoji:
            cursor = self.editor.textCursor()
            cursor.insertText(picker.selected_emoji)
            self.editor.setFocus()

    def delete_card(self):
        reply = QMessageBox.question(
            self,
            tr("delete_todo_confirm", "Delete Task?"),
            f"{tr('delete_todo_confirm', 'Delete')} '{self.title_input.text()}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.deleted = True
            self.accept()

    def save_card(self):
        self.accept()


class KanbanColumnWidget(QFrame):
    """
    A single column in the Kanban board (e.g. To Do, In Progress, Done).
    Theme-adaptive styling without hardcoded light/dark colors.
    """
    def __init__(self, board, column_name):
        super().__init__()
        self.board = board
        self.column_name = column_name
        self.init_ui()

    def init_ui(self):
        self.setFixedWidth(270)
        self.setStyleSheet("""
            KanbanColumnWidget {
                background-color: rgba(128, 128, 128, 0.08);
                border: 1px solid rgba(128, 128, 128, 0.22);
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        header.setSpacing(6)

        self.title_label = QLabel(self.column_name)
        self.title_label.setStyleSheet("font-weight: 700; font-size: 13px;")
        header.addWidget(self.title_label)

        self.badge = QLabel("0")
        self.badge.setStyleSheet("""
            background-color: rgba(128, 128, 128, 0.22);
            border-radius: 9px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: 600;
        """)
        header.addWidget(self.badge)

        header.addStretch()

        # Add card to this column button
        self.add_btn = QPushButton("➕")
        self.add_btn.setFixedSize(26, 26)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setToolTip(f"Add task to {self.column_name}")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.25);
            }
        """)
        self.add_btn.clicked.connect(lambda: self.board.add_card_to_column(self.column_name))
        header.addWidget(self.add_btn)

        # Menu button
        self.menu_btn = QPushButton("⋮")
        self.menu_btn.setFixedSize(26, 26)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.25);
            }
        """)
        self.menu_btn.clicked.connect(self.show_column_menu)
        header.addWidget(self.menu_btn)

        layout.addLayout(header)

        # Cards list
        self.list_widget = KanbanListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

    def on_item_double_clicked(self, item):
        todo_id = item.data(Qt.UserRole)
        if todo_id:
            self.board.open_card_dialog(todo_id)

    def show_column_menu(self):
        menu = QMenu(self)
        act_rename = menu.addAction(tr("rename_column", "Rename Column"))
        act_delete = menu.addAction(tr("delete_column", "Delete Column"))

        action = menu.exec(self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))
        if action == act_rename:
            self.board.rename_column(self.column_name)
        elif action == act_delete:
            self.board.delete_column(self.column_name)

    def update_badge(self):
        visible_count = sum(1 for i in range(self.list_widget.count()) if not self.list_widget.item(i).isHidden())
        self.badge.setText(str(visible_count))


class KanbanBoardWidget(QWidget):
    """
    Full Kanban Board container with horizontal scrolling, columns, and search filtering.
    """
    card_updated = Signal()

    def __init__(self, main_window, project_id):
        super().__init__()
        self.main_window = main_window
        self.project_id = project_id
        self.todos_collection = self.main_window.db.todos
        self.projects_collection = self.main_window.db.projects
        self.columns = []
        self.column_widgets = {}
        self.current_query = ""

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Scroll area for horizontal Kanban board
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        self.board_content = QWidget()
        self.board_layout = QHBoxLayout(self.board_content)
        self.board_layout.setContentsMargins(10, 10, 10, 10)
        self.board_layout.setSpacing(14)
        self.board_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll_area.setWidget(self.board_content)
        self.layout.addWidget(self.scroll_area)

    def load_columns(self):
        """Loads columns from project document or defaults to default columns."""
        project = None
        if self.project_id:
            try:
                oid = ObjectId(self.project_id) if isinstance(self.project_id, str) else self.project_id
                project = self.projects_collection.find_one({"_id": oid})
            except Exception:
                project = self.projects_collection.find_one({"_id": str(self.project_id)})

        if project and "todo_columns" in project and isinstance(project["todo_columns"], list) and project["todo_columns"]:
            self.columns = list(project["todo_columns"])
        else:
            self.columns = get_default_columns()

    def save_columns(self):
        if self.project_id:
            try:
                oid = ObjectId(self.project_id) if isinstance(self.project_id, str) else self.project_id
                self.projects_collection.update_one(
                    {"_id": oid},
                    {"$set": {"todo_columns": self.columns}}
                )
            except Exception:
                self.projects_collection.update_one(
                    {"_id": str(self.project_id)},
                    {"$set": {"todo_columns": self.columns}}
                )

    def refresh_board(self):
        """Rebuilds the board columns and populates cards."""
        while self.board_layout.count() > 0:
            item = self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.column_widgets = {}
        self.load_columns()

        if not self.columns:
            self.columns = get_default_columns()

        for col_name in self.columns:
            col_widget = KanbanColumnWidget(self, col_name)
            self.column_widgets[col_name] = col_widget
            self.board_layout.addWidget(col_widget)

        # Add Column button at the end of the columns
        self.add_col_btn = QPushButton(tr("add_column", "➕ Add Column"))
        self.add_col_btn.setFixedSize(140, 42)
        self.add_col_btn.setCursor(Qt.PointingHandCursor)
        self.add_col_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 128, 128, 0.08);
                border: 1px dashed rgba(128, 128, 128, 0.35);
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.20);
            }
        """)
        self.add_col_btn.clicked.connect(self.prompt_add_column)
        self.board_layout.addWidget(self.add_col_btn, alignment=Qt.AlignTop)

        self.populate_cards()

    def populate_cards(self):
        """Loads todos from Mongita and places them in their respective column lists."""
        if not self.project_id:
            return

        for col_widget in self.column_widgets.values():
            col_widget.list_widget.clear()

        # Query all todos for this project
        todos = list(self.todos_collection.find({"project_id": str(self.project_id)}))
        first_col = self.columns[0] if self.columns else "To Do"

        for todo in todos:
            col = todo.get("status") or todo.get("column")
            # If not assigned or doesn't match any column, put in the first column (e.g. To Do)
            if not col or col not in self.column_widgets:
                col = first_col

            col_widget = self.column_widgets.get(col)
            if not col_widget:
                continue

            title = todo.get("title", "Untitled")
            content = todo.get("content", "")
            snippet, badge, is_all_done = extract_card_metadata(content)

            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, str(todo["_id"]))
            item.setData(Qt.UserRole + 1, snippet)
            item.setData(Qt.UserRole + 2, badge)
            item.setData(Qt.UserRole + 3, is_all_done)

            col_widget.list_widget.addItem(item)

        for col_widget in self.column_widgets.values():
            col_widget.update_badge()

        if self.current_query:
            self.filter_cards(self.current_query)

    def on_card_dropped(self, todo_id, target_column):
        """Called when a card is dropped into a column."""
        try:
            oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
            self.todos_collection.update_one(
                {"_id": oid},
                {"$set": {"status": target_column, "column": target_column}}
            )
        except Exception as e:
            print(f"Error updating todo on drop: {e}")

        for col_widget in self.column_widgets.values():
            col_widget.update_badge()

        if hasattr(self.main_window, "show_snackbar"):
            self.main_window.show_snackbar(f"{tr('card_moved', 'Moved to')} '{target_column}'", 1800)

        self.card_updated.emit()

    def add_card_to_column(self, column_name):
        """Quickly adds a new card directly to the specified column."""
        new_todo = {
            "title": tr("default_new_todo_title", "New Task"),
            "content": tr("default_new_task", "☐ My first task"),
            "project_id": str(self.project_id),
            "status": column_name,
            "column": column_name
        }
        res = self.todos_collection.insert_one(new_todo)
        self.populate_cards()
        self.card_updated.emit()
        if hasattr(self.main_window, "show_snackbar"):
            self.main_window.show_snackbar(f"{tr('default_new_todo_title', 'New Task')} added to '{column_name}'", 2000)

    def open_card_dialog(self, todo_id):
        """Opens modal editor for a card."""
        todo = None
        try:
            oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
            todo = self.todos_collection.find_one({"_id": oid})
        except Exception:
            todo = self.todos_collection.find_one({"_id": str(todo_id)})

        if not todo:
            return

        dialog = KanbanCardDialog(self, todo, self.columns, self)
        if dialog.exec():
            if dialog.deleted:
                try:
                    oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
                    self.todos_collection.delete_one({"_id": oid})
                except Exception:
                    self.todos_collection.delete_one({"_id": str(todo_id)})

                if hasattr(self.main_window, "show_snackbar"):
                    self.main_window.show_snackbar(tr("status_saved", "Task deleted"), 2000)
            else:
                new_title = dialog.title_input.text()
                new_content = dialog.editor.toMarkdown()
                new_col = dialog.col_combo.currentText()
                try:
                    oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
                    self.todos_collection.update_one(
                        {"_id": oid},
                        {"$set": {
                            "title": new_title,
                            "content": new_content,
                            "status": new_col,
                            "column": new_col
                        }}
                    )
                except Exception:
                    self.todos_collection.update_one(
                        {"_id": str(todo_id)},
                        {"$set": {
                            "title": new_title,
                            "content": new_content,
                            "status": new_col,
                            "column": new_col
                        }}
                    )

                if hasattr(self.main_window, "show_snackbar"):
                    self.main_window.show_snackbar(tr("status_saved", "Task saved"), 2000)

            self.populate_cards()
            self.card_updated.emit()

    def prompt_add_column(self):
        """Prompts user to add a new column."""
        name, ok = QInputDialog.getText(
            self,
            tr("add_column", "Add Column"),
            tr("add_column_prompt", "Column name:")
        )
        name = name.strip()
        if ok and name:
            if name in self.columns:
                QMessageBox.warning(self, "Warning", f"Column '{name}' already exists.")
                return
            self.columns.append(name)
            self.save_columns()
            self.refresh_board()
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(f"Column '{name}' added", 2000)
            self.card_updated.emit()

    def rename_column(self, old_name):
        """Renames an existing column and updates all tasks assigned to it."""
        new_name, ok = QInputDialog.getText(
            self,
            tr("rename_column", "Rename Column"),
            tr("add_column_prompt", "Column name:"),
            QLineEdit.Normal,
            old_name
        )
        new_name = new_name.strip()
        if ok and new_name and new_name != old_name:
            if new_name in self.columns:
                QMessageBox.warning(self, "Warning", f"Column '{new_name}' already exists.")
                return
            idx = self.columns.index(old_name)
            self.columns[idx] = new_name
            self.save_columns()

            # Update tasks assigned to old_name
            self.todos_collection.update_many(
                {"project_id": str(self.project_id), "status": old_name},
                {"$set": {"status": new_name, "column": new_name}}
            )
            self.refresh_board()
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(f"Column renamed to '{new_name}'", 2000)
            self.card_updated.emit()

    def delete_column(self, col_name):
        """Deletes a column after confirmation and migrates its cards to the first column."""
        if len(self.columns) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the only column.")
            return

        target_col = [c for c in self.columns if c != col_name][0]
        reply = QMessageBox.question(
            self,
            tr("delete_column", "Delete Column"),
            f"Delete column '{col_name}' and move its tasks to '{target_col}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.columns.remove(col_name)
            self.save_columns()

            # Move cards to target column
            self.todos_collection.update_many(
                {"project_id": str(self.project_id), "status": col_name},
                {"$set": {"status": target_col, "column": target_col}}
            )
            self.refresh_board()
            if hasattr(self.main_window, "show_snackbar"):
                self.main_window.show_snackbar(f"Column '{col_name}' deleted", 2000)
            self.card_updated.emit()

    def filter_cards(self, query: str):
        """Filters cards in all columns in real-time."""
        self.current_query = query.strip().lower()
        for col_widget in self.column_widgets.values():
            for i in range(col_widget.list_widget.count()):
                item = col_widget.list_widget.item(i)
                title = (item.text() or "").lower()
                snip = (item.data(Qt.UserRole + 1) or "").lower()
                matches = (self.current_query in title) or (self.current_query in snip)
                item.setHidden(not matches)
            col_widget.update_badge()

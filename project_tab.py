import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QListWidgetItem, QHBoxLayout, QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QCompleter, QApplication, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, Qt, QStringListModel, QSize
import json
from PySide6.QtGui import QIcon, QClipboard, QPixmap, QMovie, QPainter
from bson.objectid import ObjectId
from utils import get_resource_path, make_relative_path, open_system_terminal, open_browser
from i18n import tr

# Tamaño cuadrado uniforme del botón de preview y de su lienzo de icono.
SQUARE_SIZE = 64
ICON_SIZE = 56
ICON_MARGIN = 4


def make_square_pixmap(source, canvas=ICON_SIZE, margin=ICON_MARGIN):
    """
    Centra un pixmap en un lienzo cuadrado transparente sin recortar ni
    deformar la imagen (Qt.KeepAspectRatio + margen interno).
    """
    if source is None or source.isNull():
        return QPixmap()

    target = QPixmap(canvas, canvas)
    target.fill(Qt.transparent)

    inner = max(1, canvas - margin * 2)
    scaled = source.scaled(inner, inner, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    painter = QPainter(target)
    painter.drawPixmap(
        (canvas - scaled.width()) // 2,
        (canvas - scaled.height()) // 2,
        scaled,
    )
    painter.end()
    return target


def square_icon(source):
    """QIcon cuadrado (56x56) para el preview del proyecto."""
    return QIcon(make_square_pixmap(source, ICON_SIZE, ICON_MARGIN))

class ProjectTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()

        # ── Header: preview clicable del icono + nombre ─────────────────────
        self.change_icon_button = QPushButton()
        self.change_icon_button.setFixedSize(SQUARE_SIZE, SQUARE_SIZE)
        self.change_icon_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.change_icon_button.setText("")
        self.change_icon_button.setCursor(Qt.PointingHandCursor)
        self.change_icon_button.setToolTip(tr("btn_gif"))
        self.change_icon_button.setEnabled(False)
        self.change_icon_button.clicked.connect(self.change_icon)
        self.change_icon_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 128, 128, 0.05);
                border: 1px solid rgba(128, 128, 128, 0.35);
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.15);
                border-color: rgba(128, 128, 128, 0.6);
            }
            QPushButton:disabled {
                border: 1px dashed rgba(128, 128, 128, 0.35);
            }
        """)
        self.icon_movie = None

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.addWidget(self.change_icon_button, 0, Qt.AlignTop)

        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)
        self.name_label = QLabel(tr("project_name"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input)
        header_layout.addLayout(name_layout, 1)

        layout.addLayout(header_layout)

        self._update_project_icon_preview(None)

        self.description_label = QLabel(tr("project_description"))
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        layout.addWidget(self.description_label)
        layout.addWidget(self.description_input)

        # ── Toolbar: Key | Value | Action | Category ────────────────────────
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(8)

        self.info_name_input = QLineEdit()
        self.info_name_input.setPlaceholderText(tr("key_placeholder"))

        self.info_value_input = QLineEdit()
        self.info_value_input.setPlaceholderText(tr("value_placeholder"))

        self.action_selector = QComboBox()
        self.action_selector.addItems([tr("action_none"), tr("action_terminal"), tr("action_browser")])
        self.action_selector.setFixedWidth(120)

        # Category selector — editable para escribir nueva categoría
        self.category_selector = QComboBox()
        self.category_selector.setEditable(True)
        self.category_selector.setInsertPolicy(QComboBox.NoInsert)
        self.category_selector.lineEdit().setPlaceholderText(tr("category_placeholder"))
        self.category_selector.setFixedWidth(128)
        self._cat_completer = QCompleter(self)
        self._cat_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._cat_completer.setFilterMode(Qt.MatchContains)
        self.category_selector.setCompleter(self._cat_completer)

        self.toolbar_layout.addWidget(self.info_name_input)
        self.toolbar_layout.addWidget(self.info_value_input)
        self.toolbar_layout.addWidget(self.action_selector)
        self.toolbar_layout.addWidget(self.category_selector)

        layout.addLayout(self.toolbar_layout)

        # ── Table ────────────────────────────────────────────────────────────
        self.additional_info_table = QTableWidget(0, 3)
        self.additional_info_table.setHorizontalHeaderLabels([tr("table_key"), tr("table_value"), tr("table_actions")])
        self.additional_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.additional_info_table.setAlternatingRowColors(True)
        self.additional_info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.additional_info_table)

        # ── Save button (bottom) ──────────────────────────────────────────────
        self.save_all_button = QPushButton(tr("btn_save"))
        self.save_all_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                padding: 7px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.save_all_button.clicked.connect(self.save_project_and_info)
        layout.addWidget(self.save_all_button)

        self.setLayout(layout)

    # ─────────────────────────────────────────────────────────────────────────
    # Categories helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_all_categories(self) -> list:
        """Unique categories used by this project's info items."""
        cats = set()
        info = getattr(self.main_window, 'current_project_info', {})
        for item in info.values():
            if isinstance(item, dict):
                cat = item.get('category', '')
                if cat:
                    cats.add(cat)
        return sorted(cats)

    def _refresh_category_selector(self):
        """Rellena el combo con las categorías existentes (sin borrar lo escrito)."""
        cats = self._get_all_categories()
        current_text = self.category_selector.currentText()
        self.category_selector.blockSignals(True)
        self.category_selector.clear()
        self.category_selector.addItem("")          # opción vacía = sin categoría
        for cat in cats:
            self.category_selector.addItem(cat)
        self._cat_completer.setModel(self.category_selector.model())
        # Restaurar lo que había escrito
        self.category_selector.setCurrentText(current_text)
        self.category_selector.blockSignals(False)

    def _sync_info_tab_filter(self):
        """Actualiza el filtro de Information tab con las categorías actuales."""
        if hasattr(self.main_window, 'project_info_tab'):
            self.main_window.project_info_tab.update_categories_filter(
                self._get_all_categories()
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Save logic
    # ─────────────────────────────────────────────────────────────────────────

    @Slot()
    def save_project_and_info(self):
        key = self.info_name_input.text().strip()
        value = self.info_value_input.text().strip()

        if key and value:
            self.add_project_info_logic(key, value)

        self.save_project_metadata()

    def add_project_info_logic(self, name, value):
        idx = self.action_selector.currentIndex()
        action_type = [None, "terminal", "browser"][idx]
        category = self.category_selector.currentText().strip()

        info_data = {"value": value, "action": action_type, "category": category}
        self.main_window.current_project_info[name] = info_data
        self.add_info_item(name, value, action_type)

        self.info_name_input.clear()
        self.info_value_input.clear()
        self.action_selector.setCurrentIndex(0)
        self.category_selector.setCurrentIndex(0)

        self._refresh_category_selector()
        self._sync_info_tab_filter()

    def save_project_metadata(self):
        project_name = self.name_input.text().strip()
        project_description = self.description_input.toPlainText().strip()

        if not project_name:
            return

        projects_collection = self.main_window.db.projects

        if self.main_window.current_project_item is None:
            default_path = "assets/project_images/default_icon.png"
            project_doc = {
                "name": project_name,
                "description": project_description,
                "info": self.main_window.current_project_info,
                "icon_path": default_path
            }
            result = projects_collection.insert_one(project_doc)
            self.main_window.current_project_id = str(result.inserted_id)

            new_item = QListWidgetItem(f"{project_name}: {project_description[:8]}...")
            new_item.setIcon(QIcon(default_path))
            new_item.setData(Qt.UserRole, self.main_window.current_project_id)
            new_item.setData(Qt.UserRole + 1, default_path)
            self.main_window.project_list_widget.addItem(new_item)
            self.main_window.current_project_item = new_item

            self.change_icon_button.setEnabled(True)

        else:
            p_id = self.main_window.current_project_id
            if isinstance(p_id, str): p_id = ObjectId(p_id)

            projects_collection.update_one(
                {"_id": p_id},
                {"$set": {
                    "name": project_name,
                    "description": project_description,
                    "info": self.main_window.current_project_info
                }}
            )

            self.main_window.current_project_name = project_name
            self.main_window.current_project_description = project_description
            self.main_window.current_project_item.setText(f"{project_name}: {project_description[:8]}...")

        self.main_window.statusBar().showMessage(f"Project '{project_name}' saved!", 3000)

        if hasattr(self.main_window, 'project_info_tab'):
            self.main_window.project_info_tab.update_project_info(
                project_name, project_description, self.main_window.current_project_info
            )

    @Slot()
    def change_icon(self):
        initial_dir = os.path.join(os.getcwd(), "assets/project_images")
        icon_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", initial_dir, "Images (*.gif *.png *.ico *.webp)")

        if icon_path:
            stored_path = make_relative_path(icon_path)
            if hasattr(self.main_window, 'current_project_id') and self.main_window.current_project_id:
                try:
                    p_id = self.main_window.current_project_id
                    if isinstance(p_id, str):
                        p_id = ObjectId(p_id)
                    result = self.main_window.db.projects.update_one(
                        {"_id": p_id},
                        {"$set": {"icon_path": stored_path}}
                    )
                    if result.modified_count == 0:
                        self.main_window.db.projects.update_one(
                            {"name": self.name_input.text()},
                            {"$set": {"icon_path": stored_path}}
                        )
                except Exception as e:
                    print(f"ERROR al guardar icono: {e}")

            if self.main_window.current_project_item:
                self.main_window.current_project_item.setIcon(QIcon(icon_path))
                self.main_window.current_project_item.setData(Qt.UserRole + 1, icon_path)

            self.main_window.update_project_icon(self.name_input.text(), icon_path)
            # Refrescar la previsualización de la cabecera (GIF o imagen)
            self._update_project_icon_preview(stored_path)

    def _stop_icon_movie(self):
        """Detiene y libera la animación actual de la previsualización."""
        if self.icon_movie is not None:
            try:
                self.icon_movie.frameChanged.disconnect(self._on_icon_frame)
            except (RuntimeError, TypeError):
                pass
            try:
                self.icon_movie.stop()
            except Exception:
                pass
            self.icon_movie = None

    def _on_icon_frame(self, _frame):
        """Actualiza el icono del botón de preview con el frame actual del GIF."""
        if self.icon_movie is not None:
            pixmap = self.icon_movie.currentPixmap()
            if not pixmap.isNull():
                self.change_icon_button.setIcon(square_icon(pixmap))

    def _update_project_icon_preview(self, icon_path):
        """Muestra el icono/GIF del proyecto en el botón de preview."""
        self._stop_icon_movie()

        if not icon_path:
            icon_path = "assets/project_images/default_icon.png"

        resolved = icon_path if os.path.isabs(icon_path) else get_resource_path(icon_path)
        if not os.path.exists(resolved):
            resolved = get_resource_path("assets/project_images/default_icon.png")
        if not os.path.exists(resolved):
            self.change_icon_button.setIcon(QIcon())
            return

        is_gif = str(icon_path).lower().endswith(".gif") or resolved.lower().endswith(".gif")
        if is_gif:
            movie = QMovie(resolved)
            if movie.isValid():
                self.icon_movie = movie
                movie.frameChanged.connect(self._on_icon_frame)
                movie.start()
                self._on_icon_frame(0)
                return

        pixmap = QPixmap(resolved)
        if not pixmap.isNull():
            self.change_icon_button.setIcon(square_icon(pixmap))
        else:
            self.change_icon_button.setIcon(QIcon())

    def reset_icon_preview(self):
        """Vuelve al icono por defecto (por ejemplo al crear un proyecto)."""
        self._update_project_icon_preview(None)

    # ─────────────────────────────────────────────────────────────────────────
    # Load / display
    # ─────────────────────────────────────────────────────────────────────────

    def update_project_form(self, name, description):
        self.name_input.setText(name)
        self.description_input.setText(description)
        self.name_input.setReadOnly(False)
        self.description_input.setReadOnly(False)
        self.change_icon_button.setEnabled(True)

        # Previsualización del icono/GIF del proyecto seleccionado
        icon_path = "assets/project_images/default_icon.png"
        current_item = getattr(self.main_window, "current_project_item", None)
        if current_item is not None:
            icon_path = current_item.data(Qt.UserRole + 1) or icon_path
        self._update_project_icon_preview(icon_path)

        self.update_additional_info_table()
        self._refresh_category_selector()
        self._sync_info_tab_filter()

    def update_additional_info_table(self):
        self.clear_table()
        info_dict = getattr(self.main_window, 'current_project_info', {})
        for key, info_item in info_dict.items():
            value = info_item["value"] if isinstance(info_item, dict) else info_item

            action = "none"
            if isinstance(info_item, dict):
                action = info_item.get("action")
                if not action and info_item.get("terminal"):
                    action = "terminal"

            self.add_info_item(key, value, action)

    def clear_table(self):
        self.additional_info_table.setRowCount(0)

    def add_info_item(self, key, value, action=None):
        row_position = self.additional_info_table.rowCount()
        self.additional_info_table.insertRow(row_position)
        self.additional_info_table.setItem(row_position, 0, QTableWidgetItem(key))
        self.additional_info_table.setItem(row_position, 1, QTableWidgetItem(value))

        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(2)
        actions_widget.setLayout(actions_layout)

        copy_button = QPushButton()
        copy_button.setIcon(QIcon(get_resource_path("assets/icons/icon_copy.png")))
        copy_button.setMaximumSize(24, 24)
        copy_button.setToolTip("Copy to clipboard")
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(value))
        actions_layout.addWidget(copy_button)

        if action == "terminal":
            term_btn = QPushButton()
            term_btn.setIcon(QIcon(get_resource_path("assets/icons/terminal.png")))
            if not os.path.exists(get_resource_path("assets/icons/terminal.png")):
                term_btn.setText(">_")
            term_btn.setMaximumSize(24, 24)
            term_btn.setToolTip("Run in Terminal")
            term_btn.clicked.connect(lambda: open_system_terminal(value))
            actions_layout.addWidget(term_btn)

        elif action == "browser":
            web_btn = QPushButton()
            web_btn.setIcon(QIcon(get_resource_path("assets/icons/browser.png")))
            if not os.path.exists(get_resource_path("assets/icons/browser.png")):
                web_btn.setText("🌐")
            web_btn.setMaximumSize(24, 24)
            web_btn.setToolTip("Open in Browser")
            web_btn.clicked.connect(lambda: open_browser(value))
            actions_layout.addWidget(web_btn)

        self.additional_info_table.setCellWidget(row_position, 2, actions_widget)

    @Slot()
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def retranslate_ui(self):
        from i18n import tr
        self.name_label.setText(tr("project_name"))
        self.description_label.setText(tr("project_description"))
        self.info_name_input.setPlaceholderText(tr("key_placeholder"))
        self.info_value_input.setPlaceholderText(tr("value_placeholder"))
        self.category_selector.lineEdit().setPlaceholderText(tr("category_placeholder"))
        self.additional_info_table.setHorizontalHeaderLabels([
            tr("table_key"), tr("table_value"), tr("table_actions")
        ])
        self.save_all_button.setText(tr("btn_save"))
        self.change_icon_button.setText("")
        self.change_icon_button.setToolTip(tr("btn_gif"))
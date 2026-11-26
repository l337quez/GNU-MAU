import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QListWidgetItem, QHBoxLayout, QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QCompleter, QApplication, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, Qt, QStringListModel
import json
from PySide6.QtGui import QIcon, QClipboard
from bson.objectid import ObjectId
from utils import (get_resource_path, make_relative_path, open_system_terminal, 
                   open_browser, encrypt_value, decrypt_value, send_api_request)
import urllib.parse


class ProjectTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()

        # ── Name & Description ──────────────────────────────────────────────
        name_label = QLabel("Project name")
        self.name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        description_label = QLabel("Project description")
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        layout.addWidget(description_label)
        layout.addWidget(self.description_input)

        # ── Toolbar: Row 1 & Row 2 layouts ───────────────────────────────────
        self.row1_layout = QHBoxLayout()
        self.row1_layout.setSpacing(8)

        self.change_icon_button = QPushButton("🖼️ Gif")
        self.change_icon_button.setFixedWidth(65)
        self.change_icon_button.setEnabled(False)
        self.change_icon_button.clicked.connect(self.change_icon)
        self.change_icon_button.setStyleSheet("""
            QPushButton { padding: 6px; border-radius: 4px; border: 1px solid #ccc; }
            QPushButton:disabled { background-color: #f0f0f0; color: #888; border: 1px solid #ddd; }
        """)

        self.info_name_input = QLineEdit()
        self.info_name_input.setPlaceholderText("Key...")

        self.info_value_input = QLineEdit()
        self.info_value_input.setPlaceholderText("Value...")

        self.encrypt_checkbox = QCheckBox("🔒 Encriptar")
        self.encrypt_checkbox.setFixedWidth(90)

        self.row1_layout.addWidget(self.change_icon_button)
        self.row1_layout.addWidget(self.info_name_input)
        self.row1_layout.addWidget(self.info_value_input)
        self.row1_layout.addWidget(self.encrypt_checkbox)

        self.row2_layout = QHBoxLayout()
        self.row2_layout.setSpacing(8)

        self.action_selector = QComboBox()
        self.action_selector.addItems(["🚫 None", "💻 Terminal", "🌐 Browser"])
        self.action_selector.setFixedWidth(120)

        # Category selector — editable para escribir nueva categoría
        self.category_selector = QComboBox()
        self.category_selector.setEditable(True)
        self.category_selector.setInsertPolicy(QComboBox.NoInsert)
        self.category_selector.lineEdit().setPlaceholderText("Category")
        self.category_selector.setFixedWidth(128)
        self._cat_completer = QCompleter(self)
        self._cat_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._cat_completer.setFilterMode(Qt.MatchContains)
        self.category_selector.setCompleter(self._cat_completer)

        self.row2_layout.addWidget(self.action_selector)
        self.row2_layout.addWidget(self.category_selector)
        self.row2_layout.addStretch()

        self.toolbar_container = QVBoxLayout()
        self.toolbar_container.setSpacing(6)
        self.toolbar_container.addLayout(self.row1_layout)
        self.toolbar_container.addLayout(self.row2_layout)

        layout.addLayout(self.toolbar_container)

        # ── Table ────────────────────────────────────────────────────────────
        self.additional_info_table = QTableWidget(0, 3)
        self.additional_info_table.setHorizontalHeaderLabels(["Key", "Value", "Actions"])
        self.additional_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.additional_info_table.setAlternatingRowColors(True)
        self.additional_info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.additional_info_table)

        # ── Save button (bottom) ──────────────────────────────────────────────
        self.save_all_button = QPushButton("💾 Save")
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
        is_encrypted = self.encrypt_checkbox.isChecked()

        val_to_save = encrypt_value(value) if is_encrypted else value

        info_data = {
            "value": val_to_save,
            "action": action_type,
            "category": category,
            "encrypted": is_encrypted
        }
        self.main_window.current_project_info[name] = info_data
        self.add_info_item(name, value, action_type, is_encrypted)

        self.info_name_input.clear()
        self.info_value_input.clear()
        self.action_selector.setCurrentIndex(0)
        self.category_selector.setCurrentIndex(0)
        self.encrypt_checkbox.setChecked(False)

        self._refresh_category_selector()
        self._sync_info_tab_filter()

    def save_project_metadata(self):
        project_name = self.name_input.text().strip()
        project_description = self.description_input.toPlainText().strip()

        if not project_name:
            return

        if self.main_window.current_project_item is None:
            default_path = "assets/project_images/default_icon.png"
            project_doc = {
                "name": project_name,
                "description": project_description,
                "info": self.main_window.current_project_info,
                "icon_path": default_path
            }
            
            response = send_api_request("http://localhost:9000/api/projects/", method="POST", data=project_doc)
            if response is None:
                print("No se pudo crear el proyecto en el backend, creando localmente...")
                try:
                    res = self.main_window.db.projects.insert_one(project_doc)
                    response = {"id": str(res.inserted_id)}
                except Exception as e:
                    print(f"Error al crear proyecto localmente: {e}")

            if response and "id" in response:
                self.main_window.current_project_id = response["id"]

                new_item = QListWidgetItem(f"{project_name}: {project_description[:8]}...")
                new_item.setIcon(QIcon(default_path))
                new_item.setData(Qt.UserRole, self.main_window.current_project_id)
                new_item.setData(Qt.UserRole + 1, default_path)
                self.main_window.project_list_widget.addItem(new_item)
                self.main_window.current_project_item = new_item

                self.change_icon_button.setEnabled(True)
                self.main_window.statusBar().showMessage(f"Project '{project_name}' saved successfully!", 3000)
            else:
                self.main_window.statusBar().showMessage("Error: Could not save project.", 3000)

        else:
            p_id = self.main_window.current_project_id
            update_doc = {
                "name": project_name,
                "description": project_description,
                "info": self.main_window.current_project_info
            }
            
            response = send_api_request(f"http://localhost:9000/api/projects/{p_id}", method="PUT", data=update_doc)
            if response is None:
                print("No se pudo actualizar el proyecto en el backend, actualizando localmente...")
                try:
                    oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                    self.main_window.db.projects.update_one(
                        {"_id": oid},
                        {"$set": update_doc}
                    )
                    response = update_doc
                except Exception as e:
                    print(f"Error al actualizar proyecto localmente: {e}")

            if response:
                self.main_window.current_project_name = project_name
                self.main_window.current_project_description = project_description
                self.main_window.current_project_item.setText(f"{project_name}: {project_description[:8]}...")
                self.main_window.statusBar().showMessage(f"Project '{project_name}' updated successfully!", 3000)
            else:
                self.main_window.statusBar().showMessage("Error: Could not update project.", 3000)

        if hasattr(self.main_window, 'project_info_tab'):
            self.main_window.project_info_tab.update_project_info(
                project_name, project_description, self.main_window.current_project_info
            )

    @Slot()
    def change_icon(self):
        initial_dir = get_resource_path("assets/project_images")
        icon_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", initial_dir, "Images (*.gif *.png *.ico *.webp)")

        if icon_path:
            if hasattr(self.main_window, 'current_project_id') and self.main_window.current_project_id:
                try:
                    p_id = self.main_window.current_project_id
                    stored_path = make_relative_path(icon_path)
                    encoded_path = urllib.parse.quote(stored_path)
                    url = f"http://localhost:9000/api/projects/{p_id}/icon?icon_path={encoded_path}"
                    response = send_api_request(url, method="PATCH")
                    if response is None:
                        print("No se pudo guardar icono en el backend, actualizando localmente...")
                        try:
                            oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                            self.main_window.db.projects.update_one(
                                {"_id": oid},
                                {"$set": {"icon_path": stored_path}}
                            )
                            response = {"icon_path": stored_path}
                        except Exception as e:
                            print(f"Error al guardar icono localmente: {e}")
                    if not response:
                        print("ERROR al guardar icono")
                except Exception as e:
                    print(f"ERROR al guardar icono: {e}")

            if self.main_window.current_project_item:
                self.main_window.current_project_item.setIcon(QIcon(icon_path))
                self.main_window.current_project_item.setData(Qt.UserRole + 1, icon_path)

            self.main_window.update_project_icon(self.name_input.text(), icon_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Load / display
    # ─────────────────────────────────────────────────────────────────────────

    def update_project_form(self, name, description):
        self.name_input.setText(name)
        self.description_input.setText(description)
        self.name_input.setReadOnly(False)
        self.description_input.setReadOnly(False)
        self.change_icon_button.setEnabled(True)
        self.update_additional_info_table()
        self._refresh_category_selector()
        self._sync_info_tab_filter()

    def update_additional_info_table(self):
        self.clear_table()
        info_dict = getattr(self.main_window, 'current_project_info', {})
        for key, info_item in info_dict.items():
            is_encrypted = False
            if isinstance(info_item, dict):
                is_encrypted = info_item.get("encrypted", False)
                raw_value = info_item["value"]
                value = decrypt_value(raw_value) if is_encrypted else raw_value
            else:
                value = info_item

            action = "none"
            if isinstance(info_item, dict):
                action = info_item.get("action")
                if not action and info_item.get("terminal"):
                    action = "terminal"

            self.add_info_item(key, value, action, is_encrypted)

    def clear_table(self):
        self.additional_info_table.setRowCount(0)

    def add_info_item(self, key, value, action=None, encrypted=False):
        row_position = self.additional_info_table.rowCount()
        self.additional_info_table.insertRow(row_position)
        self.additional_info_table.setItem(row_position, 0, QTableWidgetItem(key))
        
        display_value = "••••••••" if encrypted else value
        self.additional_info_table.setItem(row_position, 1, QTableWidgetItem(display_value))

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
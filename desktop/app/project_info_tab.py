from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QScrollArea, 
                               QCompleter, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QApplication, QFileDialog, QAbstractItemView, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QIcon, QClipboard
import json, sys, os
from bson.objectid import ObjectId
from utils import (get_resource_path, make_relative_path, open_system_terminal, 
                   open_browser, is_windows, encrypt_value, decrypt_value, send_api_request)
import urllib.parse

class ProjectInfoTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.info_layout = QVBoxLayout()

        self.project_name_label = QLabel("Project name")
        self.project_name_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        self.info_layout.addWidget(self.project_name_label)


        buttons_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by key")
        self.search_input.returnPressed.connect(self.search_info)
        buttons_layout.addWidget(self.search_input)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories")
        self.category_filter.setFixedWidth(146)
        self.category_filter.currentIndexChanged.connect(self.search_info)
        buttons_layout.addWidget(self.category_filter)

        self.info_layout.addLayout(buttons_layout)

        self.confirmation_widget = QWidget()
        self.confirmation_widget.setVisible(False)
        confirm_layout = QHBoxLayout(self.confirmation_widget)
        confirm_layout.setContentsMargins(0, 5, 0, 5)
        
        self.confirm_label = QLabel("Are you sure delete this record?")
        self.confirm_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        self.confirm_yes_btn = QPushButton("Delete")
        self.confirm_yes_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px 10px;")
        self.confirm_yes_btn.clicked.connect(self.confirm_deletion)
        
        self.confirm_no_btn = QPushButton("Cancel")
        self.confirm_no_btn.setStyleSheet("padding: 5px 10px;")
        self.confirm_no_btn.clicked.connect(self.cancel_deletion)
        
        confirm_layout.addWidget(self.confirm_label)
        confirm_layout.addWidget(self.confirm_yes_btn)
        confirm_layout.addWidget(self.confirm_no_btn)
        confirm_layout.addStretch()
        
        self.info_layout.addWidget(self.confirmation_widget)
        
        self.row_to_delete = -1

        self.info_form_layout = QHBoxLayout()
        self.info_name_input = QLineEdit()
        self.info_name_input.setPlaceholderText("key")
        self.info_value_input = QLineEdit()
        self.info_value_input.setPlaceholderText("value")
        
        self.action_selector = QComboBox()
        self.action_selector.addItems(["\U0001f6ab None", "\U0001f4bb Terminal", "\U0001f310 Browser"])
        self.action_selector.setFixedWidth(110)

        self.encrypt_checkbox = QCheckBox("🔒 Encriptar")
        self.encrypt_checkbox.setFixedWidth(90)

        self.add_info_button = QPushButton("Add")
        self.add_info_button.clicked.connect(self.add_project_info)
        
        self.info_form_layout.addWidget(self.info_name_input)
        self.info_form_layout.addWidget(self.info_value_input)
        self.info_form_layout.addWidget(self.action_selector)
        self.info_form_layout.addWidget(self.encrypt_checkbox)
        self.info_form_layout.addWidget(self.add_info_button)
        self.info_layout.addLayout(self.info_form_layout)

        self.additional_info_table = QTableWidget(0, 3)
        self.additional_info_table.setHorizontalHeaderLabels(["Key", "Value", "Actions"])
        self.additional_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.additional_info_table.setAlternatingRowColors(True)
        self.additional_info_table.verticalHeader().setVisible(False)
        self.additional_info_table.setEditTriggers(QAbstractItemView.AllEditTriggers)

        self.info_layout.addWidget(self.additional_info_table)

        self.setLayout(self.info_layout)
        self.set_editing_enabled(False)


    def update_project_info(self, name, description, info):
        self.project_name_label.setText(f"Project: {name}")
        self.clear_table()
        info_dict = info if isinstance(info, dict) else {}
        for key, info_item in info_dict.items():
            is_encrypted = False
            if isinstance(info_item, dict):
                is_encrypted = info_item.get("encrypted", False)
                raw_value = info_item["value"]
                value = decrypt_value(raw_value) if is_encrypted else raw_value
            else:
                value = info_item
                
            category = ""
            action = "none"
            if isinstance(info_item, dict):
                category = info_item.get("category", "")
                action = info_item.get("action")
                if not action and info_item.get("terminal"):
                    action = "terminal"
            self.add_info_item(key, value, action, category, is_encrypted)

    def clear_table(self):
        self.additional_info_table.setRowCount(0)

    def add_info_item(self, key, value, action=None, category="", encrypted=False):
        row_position = self.additional_info_table.rowCount()
        self.additional_info_table.insertRow(row_position)
        
        key_item = QTableWidgetItem(key)
        key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        key_item.setData(Qt.UserRole, key)            # key original (para edición)
        key_item.setData(Qt.UserRole + 1, category)   # categoría asignada
        key_item.setData(Qt.UserRole + 2, encrypted)  # encriptado asignado
        self.additional_info_table.setItem(row_position, 0, key_item)
        
        display_value = "••••••••" if encrypted else value
        value_item = QTableWidgetItem(display_value)
        value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        value_item.setData(Qt.UserRole, value)        # guardar valor desencriptado original
        self.additional_info_table.setItem(row_position, 1, value_item)
        
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(1)
        actions_widget.setLayout(actions_layout)

        copy_button = QPushButton()
        copy_button.setIcon(QIcon(get_resource_path("assets/icons/icon_copy.png")))
        copy_button.setMaximumSize(24, 24)
        copy_button.clicked.connect(lambda k=key, v=value: self.copy_to_clipboard(k, v))
        actions_layout.addWidget(copy_button)

        delete_button = QPushButton()
        delete_button.setIcon(QIcon(get_resource_path("assets/icons/delete.png")))
        delete_button.setMaximumSize(24, 24)
        delete_button.clicked.connect(self.on_delete_clicked)
        actions_layout.addWidget(delete_button)

        save_button = QPushButton()
        save_button.setIcon(QIcon(get_resource_path("assets/icons/save.png")))
        save_button.setMaximumSize(24, 24)
        save_button.clicked.connect(self.on_save_clicked)
        actions_layout.addWidget(save_button)

        if action == "terminal":
            term_btn = QPushButton()
            term_btn.setIcon(QIcon(get_resource_path("assets/icons/terminal.png")))
            if not os.path.exists(get_resource_path("assets/icons/terminal.png")):
                term_btn.setText(">_")
            term_btn.setMaximumSize(24, 24)
            term_btn.setToolTip("Run Terminal")
            term_btn.clicked.connect(lambda: open_system_terminal(value))
            actions_layout.addWidget(term_btn)
        elif action == "browser":
            web_btn = QPushButton()
            web_btn.setIcon(QIcon(get_resource_path("assets/icons/browser.png")))
            if not os.path.exists(get_resource_path("assets/icons/browser.png")):
                web_btn.setText("🌐")
            web_btn.setMaximumSize(24, 24)
            web_btn.setToolTip("Open Browser")
            web_btn.clicked.connect(lambda: open_browser(value))
            actions_layout.addWidget(web_btn)

        self.additional_info_table.setCellWidget(row_position, 2, actions_widget)

    @Slot()
    def on_delete_clicked(self):
        button = self.sender()
        if button:
            from PySide6.QtCore import QPoint
            # Map point to the table's viewport for accurate index detection
            pos = button.mapTo(self.additional_info_table.viewport(), QPoint(0, 0))
            index = self.additional_info_table.indexAt(pos)
            if index.isValid():
                self.row_to_delete = index.row()
                key_item = self.additional_info_table.item(self.row_to_delete, 0)
                key_text = key_item.text() if key_item else "this record"
                self.confirm_label.setText(f"Are you sure delete {key_text}?")
                self.confirmation_widget.setVisible(True)

    @Slot()
    def confirm_deletion(self):
        if self.row_to_delete >= 0:
            self.delete_row(self.row_to_delete)
        self.cancel_deletion()

    @Slot()
    def cancel_deletion(self):
        self.row_to_delete = -1
        self.confirmation_widget.setVisible(False)

    @Slot()
    def on_save_clicked(self):
        button = self.sender()
        if button:
            from PySide6.QtCore import QPoint
            pos = button.mapTo(self.additional_info_table.viewport(), QPoint(0, 0))
            index = self.additional_info_table.indexAt(pos)
            if index.isValid():
                self.save_row(index.row())

    @Slot()
    def save_row(self, row_position):
        key_item = self.additional_info_table.item(row_position, 0)
        value_item = self.additional_info_table.item(row_position, 1)
        
        if key_item and value_item:
            old_key = key_item.data(Qt.UserRole)  # Get the original key before editing
            new_key = key_item.text()
            was_encrypted = key_item.data(Qt.UserRole + 2) or False
            
            # Si el valor sigue enmascarado y no se cambió, usar el original desencriptado
            new_value = value_item.text()
            if was_encrypted and new_value == "••••••••":
                value = value_item.data(Qt.UserRole)
            else:
                value = new_value

            # Ensure that current_project_info exists
            if not hasattr(self.main_window, 'current_project_info'):
                self.main_window.current_project_info = {}

            val_to_save = encrypt_value(value) if was_encrypted else value

            orig_action = None
            orig_cat = ""
            if old_key in self.main_window.current_project_info:
                old_info = self.main_window.current_project_info[old_key]
                if isinstance(old_info, dict):
                    orig_action = old_info.get("action")
                    orig_cat = old_info.get("category", "")

            info_item = {
                "value": val_to_save,
                "action": orig_action,
                "category": orig_cat,
                "encrypted": was_encrypted
            }

            new_info_dict = dict(self.main_window.current_project_info)
            if old_key != new_key:
                new_info_dict.pop(old_key, None)
            new_info_dict[new_key] = info_item

            p_id = self.main_window.current_project_id
            payload = {
                "info": new_info_dict
            }
            url = f"http://localhost:9000/api/projects/{p_id}"
            response = send_api_request(url, method="PUT", data=payload)
            if response is None:
                print("No se pudo guardar la fila en el backend, guardando localmente...")
                try:
                    oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                    self.main_window.db.projects.update_one(
                        {"_id": oid},
                        {"$set": {"info": new_info_dict}}
                    )
                    response = {"info": new_info_dict}
                except Exception as e:
                    print(f"Error al guardar localmente: {e}")

            if response:
                self.main_window.current_project_info = response.get("info", {})
                
                key_item.setData(Qt.UserRole, new_key)
                value_item.setData(Qt.UserRole, value)
                
                # Actualizar las categorías del filtro
                categories = sorted({
                    v.get("category", "") for v in self.main_window.current_project_info.values()
                    if isinstance(v, dict) and v.get("category", "")
                })
                self.update_categories_filter(categories)
                
                self.main_window.statusBar().showMessage(f"Key '{new_key}' saved successfully!", 2000)
            else:
                self.main_window.statusBar().showMessage("Error saving row via API", 2000)

    @Slot()
    def enable_editing(self):
        self.set_editing_enabled(True)

    def set_editing_enabled(self, enabled):
        self.info_name_input.setVisible(enabled)
        self.info_value_input.setVisible(enabled)
        self.action_selector.setVisible(enabled)
        self.encrypt_checkbox.setVisible(enabled)
        self.add_info_button.setVisible(enabled)

    @Slot()
    def search_info(self):
        search_key = self.search_input.text().lower()
        selected_cat = self.category_filter.currentText()
        filter_by_cat = selected_cat != "All categories"

        for row in range(self.additional_info_table.rowCount()):
            key_item = self.additional_info_table.item(row, 0)
            key_match = (not search_key) or (key_item and search_key in key_item.text().lower())

            if filter_by_cat:
                stored_cat = key_item.data(Qt.UserRole + 1) if key_item else ""
                cat_match = (stored_cat == selected_cat)
            else:
                cat_match = True

            if key_match and cat_match:
                self.additional_info_table.showRow(row)
            else:
                self.additional_info_table.hideRow(row)

    @Slot()
    def clear_search(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        for row in range(self.additional_info_table.rowCount()):
            self.additional_info_table.showRow(row)

    def update_categories_filter(self, categories: list):
        """
        Update the combo filter with the project categories.
        """
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories")
        for cat in sorted(categories):
            self.category_filter.addItem(cat)
        self.category_filter.blockSignals(False)

    @Slot()
    def change_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Icono", "", "Imágenes PNG (*.png);;Imágenes GIF (*.gif);;Imágenes WebP (*.webp)")
        if icon_path:
            stored_path = make_relative_path(icon_path)
            self.main_window.current_project_item.setIcon(QIcon(icon_path))
            
            p_id = self.main_window.current_project_id
            encoded_path = urllib.parse.quote(stored_path)
            url = f"http://localhost:9000/api/projects/{p_id}/icon?icon_path={encoded_path}"
            
            response = send_api_request(url, method="PATCH")
            if response is None:
                print("No se pudo actualizar el icono en el backend, actualizando localmente...")
                try:
                    oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                    self.main_window.db.projects.update_one(
                        {"_id": oid},
                        {"$set": {"icon_path": stored_path}}
                    )
                    self.main_window.update_project_icon(self.main_window.current_project_name, stored_path)
                    response = {"icon_path": stored_path}
                except Exception as e:
                    print(f"Error al actualizar icono localmente: {e}")

            if response:
                print("Icon path updated successfully.")
            else:
                print("Error updating icon.")

    @Slot()
    def add_project_info(self):
        name = self.info_name_input.text().strip()
        value = self.info_value_input.text().strip()

        if name and value:
            idx = self.action_selector.currentIndex()
            action_type = [None, "terminal", "browser"][idx]
            is_encrypted = self.encrypt_checkbox.isChecked()
            
            val_to_save = encrypt_value(value) if is_encrypted else value
            p_id = self.main_window.current_project_id
            
            params = {
                "key": name,
                "value": val_to_save,
                "encrypted": str(is_encrypted).lower(),
                "category": ""
            }
            if action_type:
                params["action"] = action_type
            
            query_string = urllib.parse.urlencode(params)
            url = f"http://localhost:9000/api/projects/{p_id}/info?{query_string}"
            
            response = send_api_request(url, method="PATCH")
            if response is None:
                print("No se pudo añadir la info en el backend, añadiendo localmente...")
                try:
                    oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                    new_info_dict = dict(self.main_window.current_project_info)
                    new_info_dict[name] = {
                        "value": val_to_save,
                        "action": action_type,
                        "category": "",
                        "encrypted": is_encrypted
                    }
                    self.main_window.db.projects.update_one(
                        {"_id": oid},
                        {"$set": {"info": new_info_dict}}
                    )
                    response = {"info": new_info_dict}
                except Exception as e:
                    print(f"Error al añadir info localmente: {e}")

            if response:
                self.main_window.current_project_info = response.get("info", {})
                self.add_info_item(name, value, action_type, "", is_encrypted)
                
                categories = sorted({
                    v.get("category", "") for v in self.main_window.current_project_info.values()
                    if isinstance(v, dict) and v.get("category", "")
                })
                self.update_categories_filter(categories)
                
                self.info_name_input.clear()
                self.info_value_input.clear()
                self.action_selector.setCurrentIndex(0)
                self.encrypt_checkbox.setChecked(False)
                self.main_window.statusBar().showMessage(f"Key '{name}' added successfully!", 2000)
            else:
                self.main_window.statusBar().showMessage("Error adding info via API", 2000)

    @Slot(str, str)
    def copy_to_clipboard(self, key, value):
        clipboard = QApplication.clipboard()
        clipboard.setText(value)
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(f"Copied key '{key}' successfully!", 2000)

    @Slot()
    def delete_row(self, row_position):
        key_item = self.additional_info_table.item(row_position, 0)
        if key_item:
            key = key_item.text()
            p_id = self.main_window.current_project_id
            
            encoded_key = urllib.parse.quote(key)
            url = f"http://localhost:9000/api/projects/{p_id}/info/{encoded_key}"
            
            response = send_api_request(url, method="DELETE")
            if response is None:
                print("No se pudo eliminar la info del backend, eliminando localmente...")
                try:
                    oid = ObjectId(p_id) if isinstance(p_id, str) else p_id
                    new_info_dict = dict(self.main_window.current_project_info)
                    new_info_dict.pop(key, None)
                    self.main_window.db.projects.update_one(
                        {"_id": oid},
                        {"$set": {"info": new_info_dict}}
                    )
                    response = {"info": new_info_dict}
                except Exception as e:
                    print(f"Error al eliminar info localmente: {e}")

            if response:
                self.main_window.current_project_info = response.get("info", {})
                self.additional_info_table.removeRow(row_position)
                
                categories = sorted({
                    v.get("category", "") for v in self.main_window.current_project_info.values()
                    if isinstance(v, dict) and v.get("category", "")
                })
                self.update_categories_filter(categories)
                
                self.main_window.statusBar().showMessage(f"Key '{key}' deleted successfully!", 2000)
            else:
                self.main_window.statusBar().showMessage(f"Error deleting key '{key}' via API.", 2000)

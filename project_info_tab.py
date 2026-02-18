from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QScrollArea, 
                               QCompleter, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QApplication, QFileDialog, QAbstractItemView, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QIcon, QClipboard
import json, sys, os
from bson.objectid import ObjectId
from utils import get_resource_path, open_system_terminal, open_browser, is_windows

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
        self.info_layout.addLayout(buttons_layout)

        # Widget de confirmación de borrado
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
        self.action_selector.addItems(["🚫 None", "💻 Terminal", "🌐 Browser"])
        self.action_selector.setFixedWidth(110)

        self.add_info_button = QPushButton("Add")
        self.add_info_button.clicked.connect(self.add_project_info)
        
        self.info_form_layout.addWidget(self.info_name_input)
        self.info_form_layout.addWidget(self.info_value_input)
        self.info_form_layout.addWidget(self.action_selector)
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
        # self.project_description_label.setText(f"Description: {description}")
        self.clear_table()
        info_dict = info if isinstance(info, dict) else {}
        for key, info_item in info_dict.items():
            value = info_item["value"] if isinstance(info_item, dict) else info_item
            
            # Soporte compatibilidad
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
        
        key_item = QTableWidgetItem(key)
        key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        key_item.setData(Qt.UserRole, key)
        self.additional_info_table.setItem(row_position, 0, key_item)
        
        value_item = QTableWidgetItem(value)
        value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
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
            old_key = key_item.data(Qt.UserRole)  # Obtén el key original antes de la edición
            new_key = key_item.text()
            value = value_item.text()

            # Asegurar que current_project_info existe
            if not hasattr(self.main_window, 'current_project_info'):
                self.main_window.current_project_info = {}

            if old_key != new_key:  # Si el key ha cambiado
                # Actualiza el diccionario del proyecto
                if old_key in self.main_window.current_project_info:
                    info_item = self.main_window.current_project_info.pop(old_key)
                    if isinstance(info_item, dict):
                        info_item["value"] = value
                        self.main_window.current_project_info[new_key] = info_item
                    else:
                        self.main_window.current_project_info[new_key] = {"value": value, "action": "none"}
                else:
                    self.main_window.current_project_info[new_key] = {"value": value, "action": "none"}
            else:
                # Si el key no ha cambiado, solo actualiza el valor
                info_item = self.main_window.current_project_info.get(new_key)
                if isinstance(info_item, dict):
                    info_item["value"] = value
                else:
                    self.main_window.current_project_info[new_key] = {"value": value, "action": "none"}

            # Actualiza la base de datos
            projects_collection = self.main_window.db.projects
            p_id = self.main_window.current_project_id
            if isinstance(p_id, str): p_id = ObjectId(p_id)

            projects_collection.update_one(
                {"_id": p_id},
                {"$set": {
                    "info": self.main_window.current_project_info
                }}
            )

            # Actualiza el key original almacenado en UserRole para futuras ediciones
            key_item.setData(Qt.UserRole, new_key)
            self.main_window.statusBar().showMessage(f"Key '{new_key}' saved successfully!", 2000)

    @Slot()
    def enable_editing(self):
        self.set_editing_enabled(True)

    def set_editing_enabled(self, enabled):
        self.info_name_input.setVisible(enabled)
        self.info_value_input.setVisible(enabled)
        self.action_selector.setVisible(enabled)
        self.add_info_button.setVisible(enabled)

    @Slot()
    def search_info(self):
        search_key = self.search_input.text().lower()
        for row in range(self.additional_info_table.rowCount()):
            item = self.additional_info_table.item(row, 0)
            if item and search_key in item.text().lower():
                self.additional_info_table.showRow(row)
            else:
                self.additional_info_table.hideRow(row)

    @Slot()
    def clear_search(self):
        self.search_input.clear()
        for row in range(self.additional_info_table.rowCount()):
            self.additional_info_table.showRow(row)

    @Slot()
    def change_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Icono", "", "Imágenes PNG (*.png);;Imágenes GIF (*.gif);;Imágenes WebP (*.webp)")
        if icon_path:
            self.main_window.current_project_item.setIcon(QIcon(icon_path))
            projects_collection = self.main_window.db.projects
            
            p_id = self.main_window.current_project_id
            if isinstance(p_id, str): p_id = ObjectId(p_id)

            result = projects_collection.update_one(
                {"_id": p_id},
                {"$set": {"icon_path": icon_path}}
            )
            print(f"Icon path updated: {result.modified_count} document(s) modified.")     

    @Slot()
    def add_project_info(self):
        name = self.info_name_input.text()
        value = self.info_value_input.text()

        if name and value:
            idx = self.action_selector.currentIndex()
            action_type = [None, "terminal", "browser"][idx]
            
            info_data = {"value": value, "action": action_type}
            self.main_window.current_project_info[name] = info_data
            self.add_info_item(name, value, action_type)

            projects_collection = self.main_window.db.projects
            p_id = self.main_window.current_project_id
            if isinstance(p_id, str): p_id = ObjectId(p_id)

            projects_collection.update_one(
                {"_id": p_id},
                {"$set": {
                    "info": self.main_window.current_project_info
                }}
            )

            self.info_name_input.clear()
            self.info_value_input.clear()
            self.action_selector.setCurrentIndex(0)

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
            if key in self.main_window.current_project_info:
                del self.main_window.current_project_info[key]
            
            projects_collection = self.main_window.db.projects
            p_id = self.main_window.current_project_id
            if isinstance(p_id, str): p_id = ObjectId(p_id)

            projects_collection.update_one(
                {"_id": p_id},
                {"$set": {
                    "info": self.main_window.current_project_info
                }}
            )
            self.additional_info_table.removeRow(row_position)
            self.main_window.statusBar().showMessage(f"Key '{key}' deleted.", 2000)

import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QListWidgetItem, QHBoxLayout, QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QCompleter, QApplication)
from PySide6.QtCore import Slot, Qt
import json
from PySide6.QtGui import QIcon, QClipboard
from bson.objectid import ObjectId

class ProjectTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()

        # Inputs
        name_label = QLabel("Project name")
        self.name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        description_label = QLabel("Project description")
        self.description_input = QTextEdit()
        layout.addWidget(description_label)
        layout.addWidget(self.description_input)

        # Botones Principales
        buttons_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.enable_editing)
        
        self.change_icon_button = QPushButton("Change Icon")
        self.change_icon_button.clicked.connect(self.change_icon)
        
        save_button = QPushButton("Project save")
        save_button.clicked.connect(self.save_project)
        
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.change_icon_button)
        buttons_layout.addWidget(save_button)
        layout.addLayout(buttons_layout)

        # Info Adicional Form
        self.info_form_layout = QHBoxLayout()
        self.info_name_input = QLineEdit()
        self.info_name_input.setPlaceholderText("key")
        self.info_value_input = QLineEdit()
        self.info_value_input.setPlaceholderText("value")
        self.add_info_button = QPushButton("Add")
        self.add_info_button.clicked.connect(self.add_project_info)
        self.info_form_layout.addWidget(self.info_name_input)
        self.info_form_layout.addWidget(self.info_value_input)
        self.info_form_layout.addWidget(self.add_info_button)
        layout.addLayout(self.info_form_layout)

        # Tabla
        self.additional_info_table = QTableWidget(0, 3)
        self.additional_info_table.setHorizontalHeaderLabels(["Key", "Value", "Actions"])
        self.additional_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.additional_info_table.setAlternatingRowColors(True)
        self.additional_info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.additional_info_table)

        self.setLayout(layout)
        self.set_editing_enabled(False)

    @Slot()
    def enable_editing(self):
        self.name_input.setReadOnly(False)
        self.description_input.setReadOnly(False)
        self.set_editing_enabled(True)

    def set_editing_enabled(self, enabled):
        self.info_name_input.setVisible(enabled)
        self.description_input.setVisible(enabled) 
        self.info_value_input.setVisible(enabled)
        self.add_info_button.setVisible(enabled)
        self.edit_button.setEnabled(not enabled)

    @Slot()
    def change_icon(self):
        initial_dir = os.path.join(os.getcwd(), "assets/project_images")
        icon_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", initial_dir, "Images (*.gif *.png *.ico *.webp)")
        
        if icon_path:
            # 1. Intentar guardar en DB inmediatamente
            if hasattr(self.main_window, 'current_project_id') and self.main_window.current_project_id:
                try:
                    # Aseguramos que el ID sea un ObjectId para que la DB lo encuentre
                    p_id = self.main_window.current_project_id
                    if isinstance(p_id, str):
                        p_id = ObjectId(p_id)

                    # Intentamos la actualización
                    result = self.main_window.db.projects.update_one(
                        {"_id": p_id},
                        {"$set": {"icon_path": icon_path}}
                    )

                    # Si no se modificó nada por ID, intentamos por Nombre (Plan B)
                    if result.modified_count == 0:
                        self.main_window.db.projects.update_one(
                            {"name": self.name_input.text()},
                            {"$set": {"icon_path": icon_path}}
                        )
                    
                    print(f"DEBUG: Icono guardado físicamente en DB: {icon_path}")
                except Exception as e:
                    print(f"DEBUG ERROR al guardar icono: {e}")

            # 2. Actualizar visualmente la lista (sidebar)
            if self.main_window.current_project_item:
                self.main_window.current_project_item.setIcon(QIcon(icon_path))
                # Guardamos la ruta en el item para que persista en la sesión
                self.main_window.current_project_item.setData(Qt.UserRole + 1, icon_path)
            
            # 3. Refrescar el icono en el resto de la interfaz
            self.main_window.update_project_icon(self.name_input.text(), icon_path)

    @Slot()
    def save_project(self):
        project_name = self.name_input.text()
        project_description = self.description_input.toPlainText()

        if not project_name or not project_description:
            return

        projects_collection = self.main_window.db.projects

        # Caso: Proyecto Nuevo
        if self.main_window.current_project_item is None:
            default_path = "assets/project_images/default_icon.png"
            project_doc = {
                "name": project_name,
                "description": project_description,
                "info": {}, 
                "icon_path": default_path 
            }
            result = projects_collection.insert_one(project_doc)
            self.main_window.current_project_id = result.inserted_id
            
            # Crear item en lista
            new_item = QListWidgetItem(f"{project_name}: {project_description[:8]}...")
            new_item.setIcon(QIcon(default_path))
            new_item.setData(Qt.UserRole, self.main_window.current_project_id)
            new_item.setData(Qt.UserRole + 1, default_path)
            self.main_window.project_list_widget.addItem(new_item)
            self.main_window.current_project_item = new_item
            print("DEBUG: Nuevo proyecto creado.")

        # Caso: Proyecto Existente
        else:
            # IMPORTANTE: Aquí NO incluimos icon_path para que sea INDEPENDIENTE
            projects_collection.update_one(
                {"_id": self.main_window.current_project_id},
                {"$set": {
                    "name": project_name,
                    "description": project_description,
                    "info": self.main_window.current_project_info
                }}
            )
            
            # Actualizar solo el texto del item
            self.main_window.current_project_item.setText(f"{project_name}: {project_description[:8]}...")
            print(f"DEBUG: Texto del proyecto {self.main_window.current_project_id} actualizado.")

        self.name_input.setReadOnly(True)
        self.description_input.setReadOnly(True)
        self.set_editing_enabled(False)


    @Slot()
    def add_project_info(self):
        name = self.info_name_input.text()
        value = self.info_value_input.text()
        if name and value:
            # 1. Actualizar el diccionario en memoria
            self.main_window.current_project_info[name] = value
            self.add_info_item(name, value)
            
            # 2. Guardar en la base de datos
            if self.main_window.current_project_id:
                p_id = self.main_window.current_project_id
                if isinstance(p_id, str):
                    try:
                        p_id = ObjectId(p_id)
                    except:
                        pass
                
                self.main_window.db.projects.update_one(
                    {"_id": p_id},
                    {"$set": {"info": self.main_window.current_project_info}}
                )
            
            if hasattr(self.main_window, 'project_info_tab'):
                self.main_window.project_info_tab.update_project_info(
                    self.main_window.current_project_name,
                    self.main_window.current_project_description,
                    self.main_window.current_project_info
                )

            self.info_name_input.clear()
            self.info_value_input.clear()



    def update_project_form(self, name, description):
        self.name_input.setText(name)
        self.description_input.setText(description)
        self.name_input.setReadOnly(True)
        self.description_input.setReadOnly(True)
        self.update_additional_info_table()

    def update_additional_info_table(self):
        self.clear_table()
        info_dict = getattr(self.main_window, 'current_project_info', {})
        for key, value in info_dict.items():
            self.add_info_item(key, value)

    def clear_table(self):
        self.additional_info_table.setRowCount(0)

    def add_info_item(self, key, value):
        row_position = self.additional_info_table.rowCount()
        self.additional_info_table.insertRow(row_position)
        self.additional_info_table.setItem(row_position, 0, QTableWidgetItem(key))
        self.additional_info_table.setItem(row_position, 1, QTableWidgetItem(value))
        copy_button = QPushButton()
        copy_button.setIcon(QIcon("assets/icons/icon_copy.png"))
        copy_button.setMaximumSize(24, 24)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(value))
        self.additional_info_table.setCellWidget(row_position, 2, copy_button)

    @Slot()
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QListWidgetItem, QHBoxLayout, QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QCompleter, QApplication, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, Qt
import json
from PySide6.QtGui import QIcon, QClipboard
from bson.objectid import ObjectId
from utils import get_resource_path, open_system_terminal, open_browser
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
        self.description_input.setMaximumHeight(60) # Altura reducida
        layout.addWidget(description_label)
        layout.addWidget(self.description_input)

        # Toolbar (Single Unified Row)
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(10)

        self.change_icon_button = QPushButton("🖼️")
        self.change_icon_button.setFixedWidth(50)
        self.change_icon_button.setEnabled(False) # Bloqueado por defecto
        self.change_icon_button.clicked.connect(self.change_icon)
        
        self.info_name_input = QLineEdit()
        self.info_name_input.setPlaceholderText("Key...")
        
        self.info_value_input = QLineEdit()
        self.info_value_input.setPlaceholderText("Value...")

        
        self.action_selector = QComboBox()
        self.action_selector.addItems(["🚫 None", "💻 Terminal", "🌐 Browser"])
        self.action_selector.setFixedWidth(120)
        
        self.save_all_button = QPushButton("💾 Save")
        self.save_all_button.setFixedWidth(100)
        self.save_all_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.save_all_button.clicked.connect(self.save_project_and_info)
        
        # Sincronizar altura de botones (usando padding y mismo estilo base)
        btn_style = """
            QPushButton {
                padding: 6px; 
                border-radius: 4px;
                border: 1px solid #ccc;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #888;
                opacity: 0.5; /* Visual cue for disabled */
                border: 1px solid #ddd;
            }
        """
        self.change_icon_button.setStyleSheet(btn_style)
        
        save_btn_style = btn_style + """
            QPushButton {
                font-weight: bold; 
                background-color: #4CAF50; 
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        self.save_all_button.setStyleSheet(save_btn_style)

        self.toolbar_layout.addWidget(self.change_icon_button)
        self.toolbar_layout.addWidget(self.info_name_input)
        self.toolbar_layout.addWidget(self.info_value_input)
        self.toolbar_layout.addWidget(self.action_selector)
        self.toolbar_layout.addWidget(self.save_all_button)
        
        layout.addLayout(self.toolbar_layout)

        # Table
        self.additional_info_table = QTableWidget(0, 3)
        self.additional_info_table.setHorizontalHeaderLabels(["Key", "Value", "Actions"])
        self.additional_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.additional_info_table.setAlternatingRowColors(True)
        self.additional_info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.additional_info_table)

        self.setLayout(layout)

    
    @Slot()
    def save_project_and_info(self):
        # 1. Si hay info nueva, la agregamos
        key = self.info_name_input.text().strip()
        value = self.info_value_input.text().strip()
        
        if key and value:
            self.add_project_info_logic(key, value)
            
        # 2. Guardamos los datos base del proyecto
        self.save_project_metadata()

    def add_project_info_logic(self, name, value):
        # Actualizar el diccionario en memoria
        idx = self.action_selector.currentIndex()
        action_type = [None, "terminal", "browser"][idx]

        info_data = {"value": value, "action": action_type}
        self.main_window.current_project_info[name] = info_data
        self.add_info_item(name, value, action_type)
        
        # Limpiar inputs de info
        self.info_name_input.clear()
        self.info_value_input.clear()
        self.action_selector.setCurrentIndex(0) # Reset a None

    def save_project_metadata(self):
        project_name = self.name_input.text().strip()
        project_description = self.description_input.toPlainText().strip()

        if not project_name:
            return

        projects_collection = self.main_window.db.projects

        # Caso: Proyecto Nuevo
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
            
            # Crear item en lista
            new_item = QListWidgetItem(f"{project_name}: {project_description[:8]}...")
            new_item.setIcon(QIcon(default_path))
            new_item.setData(Qt.UserRole, self.main_window.current_project_id)
            new_item.setData(Qt.UserRole + 1, default_path)
            self.main_window.project_list_widget.addItem(new_item)
            self.main_window.current_project_item = new_item
            
            # Habilitar el botón de icono después de guardar el primer proyecto
            self.change_icon_button.setEnabled(True)
        
        # Caso: Proyecto Existente
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
            
            # Sincronizar metadatos en main_window
            self.main_window.current_project_name = project_name
            self.main_window.current_project_description = project_description

            # Actualizar solo el texto del item
            self.main_window.current_project_item.setText(f"{project_name}: {project_description[:8]}...")

        # Feedback visual
        self.main_window.statusBar().showMessage(f"Project '{project_name}' saved successfully!", 3000)
        
        # Sincronizar con la otra pestaña si existe
        if hasattr(self.main_window, 'project_info_tab'):
            self.main_window.project_info_tab.update_project_info(
                project_name, project_description, self.main_window.current_project_info
            )

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

    def update_project_form(self, name, description):
        self.name_input.setText(name)
        self.description_input.setText(description)
        # Campos siempre editables
        self.name_input.setReadOnly(False)
        self.description_input.setReadOnly(False)
        
        # Habilitar el botón de icono cuando se carga un proyecto
        self.change_icon_button.setEnabled(True)
        
        self.update_additional_info_table()

    def update_additional_info_table(self):
        self.clear_table()
        info_dict = getattr(self.main_window, 'current_project_info', {})
        for key, info_item in info_dict.items():
            value = info_item["value"] if isinstance(info_item, dict) else info_item
            
            # Soporte compatibilidad: buscar 'action' o 'terminal'
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

        # Siempre botón de copiar
        copy_button = QPushButton()
        copy_button.setIcon(QIcon(get_resource_path("assets/icons/icon_copy.png")))
        copy_button.setMaximumSize(24, 24)
        copy_button.setToolTip("Copy to clipboard")
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(value))
        actions_layout.addWidget(copy_button)

        # Botón dinámico según acción
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
# pyside imports
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                               QFileDialog, QTextEdit, QGroupBox, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, QTimer, Qt
from pacmanprogress import Pacman
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal
# Other imports
import os, json, sys, shutil
import urllib.request

REPO_VERSION_URL = "https://raw.githubusercontent.com/l337quez/GNU-MAU/main/version.txt"

class UpdateCheckThread(QThread):
    update_available = Signal(bool, str, str) 
    error_occurred = Signal(str)

    def __init__(self, local_version_path):
        super().__init__()
        self.local_path = local_version_path

    def run(self):
        local_ver = "0.0.0"
        if os.path.exists(self.local_path):
            try:
                with open(self.local_path, 'r') as f:
                    local_ver = f.read().strip()
            except: pass
        
        try:
            with urllib.request.urlopen(REPO_VERSION_URL, timeout=5) as response:
                remote_ver = response.read().decode('utf-8').strip()
        except Exception as e:
            self.error_occurred.emit(f"Error de conexión: {e}")
            return

        def parse(v): 
            v = v.lower().replace('v', '').strip()
            return tuple(map(int, (v.split('.') if '.' in v else [0])))

        if parse(remote_ver) > parse(local_ver):
            self.update_available.emit(True, local_ver, remote_ver)
        else:
            self.update_available.emit(False, local_ver, remote_ver)

class SettingTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.info_layout = QVBoxLayout()
        self.theme_layout = QHBoxLayout()
        self.theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_layout.addWidget(self.theme_combo)
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        
        self.info_layout.addLayout(self.theme_layout)

        # Map display names to internal names
        self.theme_map = {
            "Arctic Mist": "arctic_mist",
            "Amber Dusk": "amber_dusk",
            "Dark Theme": "dark_theme",
            "Light Theme": "Light Theme"
        }
        self.reverse_theme_map = {v: k for k, v in self.theme_map.items()}

        sidebar_group = QGroupBox("Sidebar position")
        sidebar_layout = QHBoxLayout()

        # Definimos las posiciones usando las constantes de Qt
        # Qt.LeftDockWidgetArea = 0x1 (1)
        # Qt.RightDockWidgetArea = 0x2 (2)
        # Qt.TopDockWidgetArea = 0x4 (4)
        # Qt.BottomDockWidgetArea = 0x8 (8)
        positions = [
            ("Left", Qt.LeftDockWidgetArea),
            ("Right", Qt.RightDockWidgetArea),
            ("Top", Qt.TopDockWidgetArea),
            ("Bottom", Qt.BottomDockWidgetArea)
        ]

        for text, pos_enum in positions:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked=False, p=pos_enum: self.change_sidebar_pos(p))
            sidebar_layout.addWidget(btn)

        sidebar_group.setLayout(sidebar_layout)
        self.info_layout.addWidget(sidebar_group)

        db_group = QGroupBox("Restore Database")
        db_group_layout = QHBoxLayout() 

        self.load_config_db_btn = QPushButton("Restore data base and storage")
        self.load_config_db_btn.setFixedWidth(200) 
        self.load_config_db_btn.clicked.connect(self.copy_files)
        db_group_layout.addWidget(self.load_config_db_btn)
        db_group_layout.addStretch()

        db_group.setLayout(db_group_layout)
        self.info_layout.addWidget(db_group)

        self.animate_button = QPushButton("Animation Start")
        self.animate_button.setFixedWidth(140) 
        self.animate_button.clicked.connect(self.start_animation)
        self.info_layout.addWidget(self.animate_button)

        self.check_update_btn = QPushButton("Find Updates")
        self.check_update_btn.setFixedWidth(140) 
        self.check_update_btn.clicked.connect(self.check_updates)
        self.info_layout.addWidget(self.check_update_btn)

        # Tray checkbox
        self.tray_checkbox = QCheckBox("Minimize to tray when closing")
        self.tray_checkbox.toggled.connect(self.toggle_tray_behavior)
        self.info_layout.addWidget(self.tray_checkbox)

        # QLabel para la barra de progreso
        self.progress_label = QLabel("")
        self.info_layout.addWidget(self.progress_label)

        # Área de texto para mostrar mensajes de error o estado
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.info_layout.addWidget(self.status_text)

        self.setLayout(self.info_layout)

        # Load config from JSON file
        config = self.load_config()
        self.current_theme = config.get("theme", "Light Theme")

        tray_setting = config.get("minimize_to_tray", True)
        self.tray_checkbox.setChecked(tray_setting)
        
        self.load_available_themes()
        
        # Set selection in combo box without triggering change_theme twice
        display_name = self.reverse_theme_map.get(self.current_theme, self.current_theme)
        index = self.theme_combo.findText(display_name)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        self.apply_theme(self.current_theme)

    def get_config_path(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".myapp")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")

    def save_config(self, updated_data):
        config_path = self.get_config_path()
        config = {}

        # Cargar config existente si existe
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

        # Actualizar solo los campos necesarios
        config.update(updated_data)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def load_config(self):
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                return json.load(config_file)
        return {}

    def get_qss_path(self, theme_name):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "themes", f"{theme_name}.qss")

    def load_available_themes(self):
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem("Light Theme")
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        themes_dir = os.path.join(base_path, "themes")
        if os.path.exists(themes_dir):
            for file in os.listdir(themes_dir):
                if file.endswith(".qss"):
                    internal_name = file.replace(".qss", "")
                    display_name = self.reverse_theme_map.get(internal_name, internal_name)
                    # Check if already added (to avoid duplicates with the base ones if any)
                    if self.theme_combo.findText(display_name) == -1:
                        self.theme_combo.addItem(display_name)
        self.theme_combo.blockSignals(False)

    def apply_theme(self, theme_name):
        if theme_name == "Light Theme":
            self.main_window.setStyleSheet("")
        else:
            qss_file = self.get_qss_path(theme_name)
            try:
                with open(qss_file, "r") as file:
                    self.main_window.setStyleSheet(file.read())
            except FileNotFoundError:
                self.status_text.append(f"Error: No se encontró {theme_name}.qss")

    @Slot(int)
    def change_theme(self, index):
        display_name = self.theme_combo.itemText(index)
        internal_name = self.theme_map.get(display_name, display_name)
        self.apply_theme(internal_name)
        self.save_config({"theme": internal_name})
        self.current_theme = internal_name

    @Slot(int)
    def change_sidebar_pos(self, pos_enum):
        """Call the function in Main to move the sidebar"""
        if hasattr(self.main_window, 'move_sidebar'):
            self.main_window.move_sidebar(pos_enum)
            self.status_text.append("Sidebar position updated.")



    @Slot()
    def copy_files(self):
        """
        Copy storage and mongita_data using an external process 
        to bypass Windows file locking.
        """
        source_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta _internal de origen")
        
        if not source_dir:
            return

        if os.path.basename(source_dir) != "_internal":
            QMessageBox.warning(self, "Incorrect folder", 
                                "You must specifically select the folder named '_internal'.")
            return

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            exe_path = sys.executable
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            exe_path = sys.argv[0]

        dest_internal = os.path.join(base_path, "_internal")

        # script bash, waiting for 2 seconds, then copy files
        batch_path = os.path.join(base_path, "update_data.bat")
        
        storage_src = os.path.join(source_dir, "storage")
        storage_dest = os.path.join(dest_internal, "storage")
        mongita_src = os.path.join(source_dir, "mongita_data")
        mongita_dest = os.path.join(dest_internal, "mongita_data")
        version_src = os.path.join(source_dir, "version.txt")
        version_dest = os.path.join(base_path, "version.txt")

        # Script compatible with Windows cmd
        batch_content = f"""
        @echo off
        timeout /t 2 /nobreak > nul
        if exist "{storage_dest}" rd /s /q "{storage_dest}"
        if exist "{mongita_dest}" rd /s /q "{mongita_dest}"
        if exist "{storage_src}" xcopy "{storage_src}" "{storage_dest}" /e /i /y
        if exist "{mongita_src}" xcopy "{mongita_src}" "{mongita_dest}" /e /i /y
        if exist "{version_src}" copy /y "{version_src}" "{version_dest}"
        start "" "{exe_path}"
        del "%~f0"
        """
        try:
            with open(batch_path, "w") as f:
                f.write(batch_content)

            self.status_text.append("Preparing update files...")
            
            QMessageBox.information(
                self,
                "Update Ready",
                "The application will close to update the data and will restart automatically."
            )

            # Ejecutar el script de forma independiente
            import subprocess
            subprocess.Popen([batch_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            sys.exit(0)

        except Exception as e:
            error_msg = f"Error in copy_files: {str(e)}"
            self.status_text.append(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to prepare update: {e}")

        

    @Slot()
    def start_animation(self):
        self.pacman = Pacman(self.progress_label, start=0, end=100, width=35, text="Progress", candy_count=35)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pacman)
        self.timer.start(100)

    @Slot()
    def update_pacman(self):
        self.pacman.update(1)
        if self.pacman.step >= self.pacman.end:
            self.timer.stop()

    @Slot()
    def on_backup_finished(self):
        self.status_text.append("Respaldo completado.")
        self.timer.stop()

    @Slot()
    def on_load_finished(self):
        self.status_text.append("Carga completada.")
        self.timer.stop()

    @Slot(bool)
    def toggle_tray_behavior(self, checked):
        self.save_config({"minimize_to_tray": checked})
        
        if hasattr(self.main_window, 'config'):
            self.main_window.config["minimize_to_tray"] = checked
        self.status_text.append(f"Minimize to tray: {'Enabled' if checked else 'Disabled'}")


    def check_updates(self):
        """
        Start finding updates
        """
        self.status_text.append("Searching for updates...")
        self.check_update_btn.setEnabled(False)

        # Search for version.txt in the same folder as the executable/script
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        if not os.path.exists(os.path.join(base_path, "version.txt")):
             base_path = os.path.dirname(__file__) 
        
        version_path = os.path.join(base_path, "version.txt")

        self.update_thread = UpdateCheckThread(version_path)
        self.update_thread.update_available.connect(self.on_update_result)
        self.update_thread.error_occurred.connect(self.on_update_error)
        self.update_thread.finished.connect(lambda: self.check_update_btn.setEnabled(True))
        self.update_thread.start()

    @Slot(bool, str, str)
    def on_update_result(self, is_available, local, remote):
        if is_available:
            msg = f"¡Versión {remote}  disponible! (Actual: {local})\n¿Ir a descargar?"
            if QMessageBox.question(self, "Update", msg) == QMessageBox.Yes:
                import webbrowser
                webbrowser.open("https://github.com/l337quez/GNU-MAU")
        else:
            QMessageBox.information(self, "Update", f"You're up to date ({local}).")
            self.status_text.append("Updated system.")

    @Slot(str)
    def on_update_error(self, error_msg):
        self.status_text.append(error_msg)
        QMessageBox.warning(self, "Error", error_msg)
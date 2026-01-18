from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                               QFileDialog, QTextEdit, QGroupBox, QCheckBox)
from PySide6.QtCore import Slot, QTimer, Qt
from pacmanprogress import Pacman
from backup_restore_threads import BackupThread, LoadThread
import os, json, sys
import urllib.request
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal


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

        def parse(v): return tuple(map(int, (v.split('.') if '.' in v else [0])))
        
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
        
        self.theme_button = QPushButton("Change Theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_layout.addWidget(self.theme_button)

        self.theme_label = QLabel("Light Theme")
        self.theme_layout.addWidget(self.theme_label)
        self.tray_checkbox = QCheckBox("Minimize to tray when closing")
        self.tray_checkbox.toggled.connect(self.toggle_tray_behavior)
        self.info_layout.addWidget(self.tray_checkbox)
        
        self.info_layout.addLayout(self.theme_layout)

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

        # Botones para respaldar y cargar la base de datos
        self.backup_button = QPushButton("Respaldo DB")
        self.backup_button.clicked.connect(self.backup_db)
        self.info_layout.addWidget(self.backup_button)

        self.load_button = QPushButton("Cargar DB")
        self.load_button.clicked.connect(self.load_db)
        self.info_layout.addWidget(self.load_button)

        # Botón para iniciar la animación de la barra de progreso
        self.animate_button = QPushButton("Iniciar Animación")
        self.animate_button.clicked.connect(self.start_animation)
        self.info_layout.addWidget(self.animate_button)

        # --- Botón de Actualizar ---
        self.check_update_btn = QPushButton("Find Updates")
        self.check_update_btn.clicked.connect(self.check_updates)
        self.info_layout.addWidget(self.check_update_btn)

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
        self.dark_mode = config.get("dark_mode", False)

        tray_setting = config.get("minimize_to_tray", True)
        self.tray_checkbox.setChecked(tray_setting)
        if self.dark_mode:
            qss_file = self.get_qss_path()
            try:
                with open(qss_file, "r") as file:
                    self.main_window.setStyleSheet(file.read())
                self.theme_label.setText("Dark Theme")
            except FileNotFoundError:
                pass 
        else:
            self.main_window.setStyleSheet("")
            self.theme_label.setText("Light Theme")

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

    def get_qss_path(self):
        if getattr(sys, 'frozen', False):
            # Estamos empaquetados con PyInstaller
            base_path = sys._MEIPASS
        else:
            # Estamos en modo de desarrollo
            base_path = os.path.dirname(__file__)
        return os.path.join(base_path, "dark_theme.qss")

    @Slot()
    def toggle_theme(self):
        config_update = {}

        if self.dark_mode:
            # Cambiar a tema claro
            self.main_window.setStyleSheet("")
            self.theme_label.setText("Light Theme")
            config_update = {"dark_mode": False}
        else:
            # Cambiar a tema oscuro
            qss_file = self.get_qss_path()
            try:
                with open(qss_file, "r") as file:
                    self.main_window.setStyleSheet(file.read())
                self.theme_label.setText("Dark Theme")
                config_update = {"dark_mode": True}
            except FileNotFoundError:
                self.status_text.append("Error: No se encontró dark_theme.qss")
                return

        self.save_config(config_update)
        self.dark_mode = not self.dark_mode

    @Slot(int)
    def change_sidebar_pos(self, pos_enum):
        """Call the function in Main to move the sidebar"""
        if hasattr(self.main_window, 'move_sidebar'):
            self.main_window.move_sidebar(pos_enum)
            self.status_text.append("Sidebar position updated.")

    @Slot()
    def backup_db(self):
        file_dialog = QFileDialog()
        file_path = QFileDialog.getExistingDirectory(self, "Guardar Respaldo de DB")
        
        if file_path:
            self.backup_thread = BackupThread(self.main_window.db_name, file_path)
            self.backup_thread.status_signal.connect(self.status_text.append)
            self.backup_thread.finished_signal.connect(self.on_backup_finished)
            self.status_text.clear()
            self.status_text.append("Iniciando respaldo...\n")

            # Iniciar el hilo de respaldo
            self.backup_thread.start()

            # Iniciar la barra de progreso Pacman
            self.pacman = Pacman(self.progress_label, start=0, end=100, width=35, text="Respaldo DB", candy_count=35)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_pacman)
            self.timer.start(100)

    @Slot()
    def load_db(self):
        file_dialog = QFileDialog()
        file_path = QFileDialog.getExistingDirectory(self, "Cargar Respaldo de DB")

        if file_path:
            self.load_thread = LoadThread(self.main_window.db_name, file_path)
            self.load_thread.status_signal.connect(self.status_text.append)
            self.load_thread.finished_signal.connect(self.on_load_finished)
            self.status_text.clear()
            self.status_text.append("Iniciando carga...\n")

            # Iniciar el hilo de carga
            self.load_thread.start()

            # Iniciar la barra de progreso Pacman
            self.pacman = Pacman(self.progress_label, start=0, end=100, width=35, text="Cargar DB", candy_count=35)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_pacman)
            self.timer.start(100)

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
        """Inicia la búsqueda de actualizaciones"""
        self.status_text.append("Buscando actualizaciones...")
        self.check_update_btn.setEnabled(False)

        # Buscar version.txt en la misma carpeta del ejecutable/script
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        if not os.path.exists(os.path.join(base_path, "version.txt")):
             base_path = os.path.dirname(__file__) # Intento secundario
        
        version_path = os.path.join(base_path, "version.txt")

        self.update_thread = UpdateCheckThread(version_path)
        self.update_thread.update_available.connect(self.on_update_result)
        self.update_thread.error_occurred.connect(self.on_update_error)
        self.update_thread.finished.connect(lambda: self.check_update_btn.setEnabled(True))
        self.update_thread.start()

    @Slot(bool, str, str)
    def on_update_result(self, is_available, local, remote):
        if is_available:
            msg = f"¡Versión {remote} disponible! (Actual: {local})\n¿Ir a descargar?"
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
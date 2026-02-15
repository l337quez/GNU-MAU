# pyside imports
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                               QFileDialog, QTextEdit, QGroupBox, QCheckBox, QComboBox)
from PySide6.QtCore import Slot, QTimer, Qt
from pacmanprogress import Pacman
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal
from reusable_progress import CustomProgressBar
# Other imports
import os, json, sys, shutil
import urllib.request
import zipfile, tarfile, tempfile
from utils import is_windows

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
            import re
            parts = re.findall(r'\d+', v)
            return tuple(map(int, parts)) if parts else (0,)

        if parse(remote_ver) > parse(local_ver):
            self.update_available.emit(True, local_ver, remote_ver)
        else:
            self.update_available.emit(False, local_ver, remote_ver)

class DownloadThread(QThread):
    progress = Signal(int)
    finished = Signal(str) # Path to downloaded file
    error = Signal(str)

    def __init__(self, url, dest_path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path

    def run(self):
        try:
            self._last_progress = -1
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    progress = int(count * block_size * 100 / total_size)
                    if progress != self._last_progress:
                        self.progress.emit(min(progress, 100))
                        self._last_progress = progress

            urllib.request.urlretrieve(self.url, self.dest_path, reporthook=report_hook)
            self.finished.emit(self.dest_path)

        except Exception as e:
            self.error.emit(str(e))

class DiscoveryThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, api_url, v_nums):
        super().__init__()
        self.api_url = api_url
        self.v_nums = v_nums

    def run(self):
        try:
            with urllib.request.urlopen(self.api_url, timeout=5) as response:
                files_json = json.loads(response.read().decode('utf-8'))
                
                target_file = None
                for f in files_json:
                    if f['type'] == 'file' and self.v_nums in f['name'] and f['name'].lower().endswith('.zip'):
                        target_file = f
                        break
                
                if target_file:
                    self.finished.emit(target_file)
                else:
                    self.error.emit(f"Compatible update (.zip) not found for version {self.v_nums}.")
        except Exception as e:
            self.error.emit(str(e))

class ExtractionThread(QThread):
    finished = Signal(str) # new_internal path
    error = Signal(str)

    def __init__(self, archive_path, temp_dir):
        super().__init__()
        self.archive_path = archive_path
        self.temp_dir = temp_dir

    def run(self):
        try:
            extract_path = os.path.join(self.temp_dir, "extracted")
            os.makedirs(extract_path, exist_ok=True)
            
            if self.archive_path.lower().endswith(".zip"):
                with zipfile.ZipFile(self.archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
            elif self.archive_path.lower().endswith(".rar"):
                raise Exception("RAR format is not supported natively by Python. Please use .ZIP for updates.")
            else:
                import shutil
                shutil.unpack_archive(self.archive_path, extract_path)
            
            new_internal = None
            for root, dirs, files in os.walk(extract_path):
                if "_internal" in dirs:
                    new_internal = os.path.join(root, "_internal")
                    break
            
            if new_internal:
                self.finished.emit(new_internal)
            else:
                self.error.emit("Could not find '_internal' folder in the update package.")
        except Exception as e:
            self.error.emit(str(e))

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

        # Restoration Section
        db_group = QGroupBox("Database and storage restoration")
        db_group_v_layout = QVBoxLayout()
        
        buttons_layout = QHBoxLayout()
        
        self.manual_restore_btn = QPushButton("Manual restoration")
        self.manual_restore_btn.setFixedWidth(160)
        self.manual_restore_btn.clicked.connect(self.copy_files)
        
        self.auto_restore_btn = QPushButton("Automatic restoration")
        self.auto_restore_btn.setFixedWidth(160)
        # Placeholder for automatic restoration logic
        self.auto_restore_btn.clicked.connect(self.check_updates)
        
        buttons_layout.addWidget(self.manual_restore_btn)
        buttons_layout.addWidget(self.auto_restore_btn)
        buttons_layout.addStretch()
        
        db_group_v_layout.addLayout(buttons_layout)
        
        # Instructional Note
        self.restoration_note = QLabel("<i>Note: for manual restoration you must select the folder where you have the data and then select the _internal folder</i>")
        self.restoration_note.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 11px;
                padding: 10px;
                border: 1px solid rgba(149, 165, 166, 0.2);
                border-radius: 5px;
                background-color: rgba(149, 165, 166, 0.05);
                margin-top: 5px;
            }
        """)
        self.restoration_note.setWordWrap(True)
        db_group_v_layout.addWidget(self.restoration_note)

        db_group.setLayout(db_group_v_layout)
        self.info_layout.addWidget(db_group)

        self.check_update_btn = QPushButton("Find Updates")
        self.check_update_btn.setFixedWidth(140) 
        self.check_update_btn.clicked.connect(self.check_updates)
        self.info_layout.addWidget(self.check_update_btn)

        # Tray checkbox
        self.tray_checkbox = QCheckBox("Minimize to tray when closing")
        self.tray_checkbox.toggled.connect(self.toggle_tray_behavior)
        self.info_layout.addWidget(self.tray_checkbox)

        # Reusable progress bar
        self.progress_bar = CustomProgressBar()
        self.info_layout.addWidget(self.progress_bar)

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
            popen_args = {"shell": True}
            if is_windows():
                # CREATE_NEW_CONSOLE is only available on Windows
                popen_args["creationflags"] = 0x00000010 # subprocess.CREATE_NEW_CONSOLE
            
            subprocess.Popen([batch_path], **popen_args)
            
            sys.exit(0)

        except Exception as e:
            error_msg = f"Error in copy_files: {str(e)}"
            self.status_text.append(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to prepare update: {e}")

        

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
            msg = f"¡Versión {remote} disponible! (Actual: {local})\n\n¿Desea actualizar automáticamente?"
            reply = QMessageBox.question(self, "Update Available", msg, 
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                self.start_auto_update(remote)
            elif reply == QMessageBox.No:
                import webbrowser
                webbrowser.open("https://github.com/l337quez/GNU-MAU")
        else:
            QMessageBox.information(self, "Update", f"You're up to date ({local}).")
            self.status_text.append("System is up to date.")

    def start_auto_update(self, version):
        self.status_text.append(f"Searching for update package for version {version}...")
        self.progress_bar.start(text="Finding Update")
        
        api_url = "https://api.github.com/repos/l337quez/GNU-MAU/contents/last_version?ref=main"
        
        import re
        parts = re.findall(r'\d+', version)
        v_nums = ".".join(parts)
        
        self.discovery_thread = DiscoveryThread(api_url, v_nums)
        self.discovery_thread.finished.connect(lambda info: self.download_target(info, version))
        self.discovery_thread.error.connect(self.on_download_error)
        self.discovery_thread.start()

    def download_target(self, file_info, version):
        file_name = file_info['name']
        download_url = file_info['download_url']
        
        self.status_text.append(f"Found: {file_name}. Downloading...")
        self.progress_bar.start(text="Downloading Update")
        
        if not hasattr(self, 'temp_dir'):
            self.temp_dir = tempfile.mkdtemp()
            
        extension = ".rar" if file_name.lower().endswith(".rar") else ".zip"
        self.download_path = os.path.join(self.temp_dir, f"update_{version}{extension}")
        
        self.download_thread = DownloadThread(download_url, self.download_path)
        self.download_thread.progress.connect(self.progress_bar.update_progress)
        self.download_thread.finished.connect(lambda path: self.start_extraction(path, version))
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_error(self, error):
        self.status_text.append(f"Update Error: {error}")
        self.progress_bar.reset()
        QMessageBox.critical(self, "Update Error", f"Failed to process update: {error}")



    def start_extraction(self, archive_path, version):
        self.status_text.append("Extracting update...")
        self.progress_bar.set_text("Extracting Update")
        
        self.extraction_thread = ExtractionThread(archive_path, self.temp_dir)
        self.extraction_thread.finished.connect(lambda path: self.on_extraction_finished(path, version))
        self.extraction_thread.error.connect(lambda err: self.on_extraction_error(err, archive_path))
        self.extraction_thread.start()

    def on_extraction_finished(self, new_internal, version):
        self.status_text.append("Update extracted. Preparing installation...")
        self.run_auto_install_script(new_internal, version)

    def on_extraction_error(self, error, archive_path):
        self.status_text.append(f"Extraction Error: {error}")
        self.progress_bar.reset()
        QMessageBox.critical(self, "Update Error", f"Failed to extract update: {error}")


    def run_auto_install_script(self, new_internal, version):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            exe_path = sys.executable
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            exe_path = sys.argv[0]

        dest_internal = os.path.join(base_path, "_internal")
        batch_path = os.path.join(base_path, "auto_update.bat")
        
        # Backup folder path
        backup_dir = os.path.join(base_path, "backup_before_update")
        
        # Paths for specific critical data
        # We'll check both root and _internal for safety
        def find_data_path(name, default_parent):
            root_path = os.path.join(base_path, name)
            internal_path = os.path.join(default_parent, name)
            if os.path.exists(root_path): return root_path
            if os.path.exists(internal_path): return internal_path
            return internal_path # Default to _internal if neither found

        storage_dest = find_data_path("storage", dest_internal)
        mongita_dest = find_data_path("mongita_data", dest_internal)
        
        storage_src = os.path.join(new_internal, "storage")
        storage_backup = os.path.join(backup_dir, "storage")
        
        mongita_src = os.path.join(new_internal, "mongita_data")
        mongita_backup = os.path.join(backup_dir, "mongita_data")
        
        # Find version.txt
        version_src = None
        search_dirs = [os.path.dirname(new_internal), new_internal]
        for sdir in search_dirs:
            v_path = os.path.join(sdir, "version.txt")
            if os.path.exists(v_path):
                version_src = v_path
                break
        
        version_dest = os.path.join(base_path, "version.txt")

        # The script will:
        # 1. Backup current data
        # 2. Update core files
        # 3. Intelligent data restore:
        #    - If ZIP has NO storage, move backup back to dest.
        #    - If ZIP HAS storage, it stays in dest (Restoration), and backup remains safe.
        
        batch_content = f"""
        @echo off
        timeout /t 3 /nobreak > nul
        
        :: 1. Create backup folder if not exists
        if not exist "{backup_dir}" mkdir "{backup_dir}"

        :: 2. Backup existing data
        :: Handling storage
        if exist "{storage_dest}" (
            echo Backing up storage...
            if exist "{storage_backup}" rd /s /q "{storage_backup}"
            move "{storage_dest}" "{storage_backup}"
        )
        
        :: Handling mongita_data (Explicitly check for existence)
        if exist "{mongita_dest}" (
            echo Backing up mongita_data...
            if exist "{mongita_backup}" rd /s /q "{mongita_backup}"
            move "{mongita_dest}" "{mongita_backup}"
        )

        :: 3. Delete old _internal and copy the new one
        :: We only delete if it exists, and handle it carefully
        if exist "{dest_internal}" (
            echo Cleaning old _internal...
            rd /s /q "{dest_internal}"
        )
        
        echo Copying new _internal...
        mkdir "{dest_internal}"
        xcopy "{new_internal}" "{dest_internal}" /s /e /i /y

        :: 4. Intelligent Restore Logic
        
        :: Check storage: if no new storage in ZIP, bring back the backup
        if not exist "{storage_src}" (
            if exist "{storage_backup}" (
                echo Restoring storage from backup...
                move "{storage_backup}" "{storage_dest}"
            )
        ) else (
            echo Using new storage from update...
            xcopy "{storage_src}" "{storage_dest}" /s /e /i /y
        )

        :: Check mongita_data: if no new data in ZIP, bring back the backup
        if not exist "{mongita_src}" (
            if exist "{mongita_backup}" (
                echo Restoring mongita_data from backup...
                move "{mongita_backup}" "{mongita_dest}"
            )
        ) else (
            echo Using new mongita_data from update...
            xcopy "{mongita_src}" "{mongita_dest}" /s /e /i /y
        )

        :: 5. Update version file
        if exist "{version_src}" copy /y "{version_src}" "{version_dest}"

        :: 6. Restart the application
        echo Restarting application...
        start "" "{exe_path}"
        del "%~f0"
        """
        
        try:
            with open(batch_path, "w") as f:
                f.write(batch_content)

            QMessageBox.information(
                self,
                "Update Ready",
                "The update has been downloaded and prepared. The application will restart to complete the installation and a backup of your data has been created in 'backup_before_update'."
            )

            import subprocess
            popen_args = {"shell": True}
            if is_windows():
                popen_args["creationflags"] = 0x00000010 
            
            subprocess.Popen([batch_path], **popen_args)
            sys.exit(0)

        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to prepare installation: {e}")



    @Slot(str)
    def on_update_error(self, error_msg):
        self.status_text.append(error_msg)
        QMessageBox.warning(self, "Error", error_msg)
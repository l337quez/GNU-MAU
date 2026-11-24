# pyside imports
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                               QFileDialog, QTextEdit, QGroupBox, QCheckBox, QComboBox,
                               QApplication)
from PySide6.QtCore import Slot, QTimer, Qt, QProcess
from pacmanprogress import Pacman
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal
from reusable_progress import CustomProgressBar
# Other imports
import os, json, sys, shutil, subprocess
import urllib.request
import zipfile, tarfile, tempfile
from utils import (get_app_dir, get_config_path, get_mongita_dir,
                   get_resource_path, get_storage_dir, load_config as load_app_config,
                   normalize_theme, save_config as save_app_config)

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
        self.current_theme = normalize_theme(config.get("theme", "Light Theme"))

        tray_setting = config.get("minimize_to_tray", True)
        self.tray_checkbox.blockSignals(True)
        self.tray_checkbox.setChecked(bool(tray_setting))
        self.tray_checkbox.blockSignals(False)
        
        self.load_available_themes()
        
        # Set selection in combo box without triggering change_theme twice
        display_name = self.reverse_theme_map.get(self.current_theme, self.current_theme)
        index = self.theme_combo.findText(display_name)
        if index >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(False)
        
        self.apply_theme(self.current_theme)

    def get_config_path(self):
        """Shared configuration path (same file used by main.py)."""
        return get_config_path()

    def save_config(self, updated_data):
        """Persist configuration through the shared helper (normalized theme)."""
        config = save_app_config(updated_data)
        if hasattr(self.main_window, "config"):
            self.main_window.config = config
        return config

    def load_config(self):
        return load_app_config()

    def get_qss_path(self, theme_name):
        return get_resource_path(os.path.join("themes", f"{normalize_theme(theme_name)}.qss"))

    def load_available_themes(self):
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem("Light Theme")

        themes_dir = get_resource_path("themes")
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
        """Apply a theme through MainWindow so both stay consistent."""
        if hasattr(self.main_window, "apply_theme"):
            if not self.main_window.apply_theme(theme_name):
                self.status_text.append(f"Error: No se encontró {normalize_theme(theme_name)}.qss")
            return

        # Fallback for standalone usage of the widget
        from utils import get_theme_stylesheet
        stylesheet = get_theme_stylesheet(theme_name)
        if stylesheet is None:
            self.status_text.append(f"Error: No se encontró {normalize_theme(theme_name)}.qss")
        else:
            self.main_window.setStyleSheet(stylesheet)

    @Slot(int)
    def change_theme(self, index):
        display_name = self.theme_combo.itemText(index)
        internal_name = normalize_theme(self.theme_map.get(display_name, display_name))
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
        Restore storage and mongita_data from a selected `_internal` folder
        using native Python file operations (Windows, Linux and macOS).
        """
        source_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta _internal de origen")

        if not source_dir:
            return

        if os.path.basename(os.path.normpath(source_dir)) != "_internal":
            QMessageBox.warning(self, "Incorrect folder",
                                "You must specifically select the folder named '_internal'.")
            return

        storage_src = os.path.join(source_dir, "storage")
        mongita_src = os.path.join(source_dir, "mongita_data")
        version_src = os.path.join(source_dir, "version.txt")

        if not any((os.path.isdir(storage_src),
                    os.path.isdir(mongita_src),
                    os.path.exists(version_src))):
            QMessageBox.warning(
                self, "Nothing to restore",
                "The selected _internal folder does not contain storage, mongita_data or version.txt.")
            return

        reply = QMessageBox.question(
            self, "Confirm restoration",
            "The current database and files will be replaced by the selected data.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.status_text.append("Restoring data...")
        try:
            # Release the database files before they are replaced
            self._close_database()

            restored = []
            if os.path.isdir(storage_src):
                self._replace_tree(storage_src, get_storage_dir())
                restored.append("storage")
            if os.path.isdir(mongita_src):
                self._replace_tree(mongita_src, get_mongita_dir())
                restored.append("mongita_data")
            if os.path.exists(version_src):
                shutil.copy2(version_src, os.path.join(get_app_dir(), "version.txt"))
                restored.append("version.txt")

            self.status_text.append(f"Restored: {', '.join(restored)}")
            QMessageBox.information(
                self, "Restoration completed",
                f"Restored: {', '.join(restored)}.\n\nThe application will restart to load the restored data.")
            self._restart_application()

        except Exception as e:
            error_msg = f"Error in copy_files: {e}"
            self.status_text.append(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to restore data: {e}")

    def _close_database(self):
        """Close the Mongita client so its files can be moved/replaced."""
        client = getattr(self.main_window, "client", None)
        if client is not None:
            try:
                client.close()
            except Exception as e:
                print(f"Could not close the database: {e}")

    @staticmethod
    def _merge_tree(source, destination):
        """Copy the contents of `source` into `destination`, keeping extras."""
        os.makedirs(destination, exist_ok=True)
        shutil.copytree(source, destination, dirs_exist_ok=True)

    @staticmethod
    def _replace_tree(source, destination):
        """
        Replace `destination` with a copy of `source` using a staging folder,
        so a failed copy does not destroy the current data.
        """
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        parent = os.path.dirname(destination) or "."
        os.makedirs(parent, exist_ok=True)

        staging_root = tempfile.mkdtemp(prefix=".mau_restore_", dir=parent)
        staged = os.path.join(staging_root, os.path.basename(destination))
        old = None
        try:
            shutil.copytree(source, staged)
            if os.path.exists(destination):
                old = os.path.join(staging_root, ".old")
                shutil.move(destination, old)
            shutil.move(staged, destination)
        except Exception:
            if old and os.path.exists(old) and not os.path.exists(destination):
                shutil.move(old, destination)
            raise
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    def _restart_application(self):
        """Restart the app with the interpreter/executable that is running it."""
        app_dir = get_app_dir()
        if getattr(sys, "frozen", False):
            program, arguments = sys.executable, []
        else:
            program, arguments = sys.executable, [os.path.join(app_dir, "main.py")]

        started = False
        try:
            result = QProcess.startDetached(program, arguments, app_dir)
            started = result[0] if isinstance(result, tuple) else bool(result)
        except Exception as e:
            print(f"QProcess restart failed: {e}")

        if not started:
            try:
                subprocess.Popen([program, *arguments], cwd=app_dir, start_new_session=True)
            except Exception as e:
                QMessageBox.critical(self, "Restart failed",
                                     f"Restored successfully, but the application could not restart: {e}")
                return

        QApplication.quit()

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
        base_path = get_app_dir()
        if not os.path.exists(os.path.join(base_path, "version.txt")):
             base_path = os.path.dirname(os.path.abspath(__file__))
        
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
        self.install_update(new_internal, version)

    def on_extraction_error(self, error, archive_path):
        self.status_text.append(f"Extraction Error: {error}")
        self.progress_bar.reset()
        QMessageBox.critical(self, "Update Error", f"Failed to extract update: {error}")

    def _backup_data(self, backup_dir):
        """
        Copy the current storage/mongita_data into <backup_dir>/data.
        Returns the backup directory, or None when there was nothing to back up.
        """
        data_backup = os.path.join(backup_dir, "data")
        os.makedirs(data_backup, exist_ok=True)

        copied = False
        for source, name in ((get_storage_dir(), "storage"),
                             (get_mongita_dir(), "mongita_data")):
            if not os.path.isdir(source):
                continue
            target = os.path.join(data_backup, name)
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(source, target)
            copied = True

        return data_backup if copied else None

    def install_update(self, new_internal, version):
        """
        Install an extracted update using native Python file operations.
        No .bat/.sh scripts are generated: backup and restore are done with
        shutil, so the same code works on Windows, Linux and macOS.
        """
        base_path = get_app_dir()
        storage_dest = get_storage_dir()
        mongita_dest = get_mongita_dir()
        backup_dir = os.path.join(base_path, "backup_before_update")

        if not getattr(sys, "frozen", False):
            try:
                self._backup_data(backup_dir)
                self.status_text.append(f"Data backup created in {backup_dir}")
                QMessageBox.information(
                    self, "Development mode",
                    "GNU Mau is running from source, so only the data backup was created.\n\n"
                    "To apply core changes, update the checkout or rebuild the Podman image.")
            except Exception as e:
                QMessageBox.critical(self, "Update Error", f"Failed to back up data: {e}")
            return

        reply = QMessageBox.question(
            self, "Install update",
            "GNU Mau will close, install the update and restart.\n"
            "Your data will be backed up in 'backup_before_update'.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        dest_internal = os.path.join(base_path, "_internal")

        def find_src_path(name):
            for folder in (new_internal, os.path.dirname(new_internal)):
                candidate = os.path.join(folder, name)
                if os.path.exists(candidate):
                    return candidate
            return None

        version_src = find_src_path("version.txt")
        version_dest = os.path.join(base_path, "version.txt")

        try:
            self.progress_bar.set_text("Installing Update")
            self.status_text.append("Closing database...")
            self._close_database()

            # 1. Back up the current data (the originals stay in place for now)
            self.status_text.append("Backing up user data...")
            backup_data = self._backup_data(backup_dir)

            # 2. Update application files
            if os.path.isdir(new_internal):
                self.status_text.append("Updating application files...")
                self._merge_tree(new_internal, dest_internal)

            # 3. Restore user data: the backup always wins over the update's
            #    bundled data. If there was no previous data, use the update's.
            self.status_text.append("Restoring user data...")
            for name, destination in (("storage", storage_dest),
                                      ("mongita_data", mongita_dest)):
                backup_src = os.path.join(backup_data, name) if backup_data else None
                fresh_src = find_src_path(name)
                if backup_src and os.path.isdir(backup_src):
                    self._replace_tree(backup_src, destination)
                elif fresh_src and os.path.isdir(fresh_src):
                    self._replace_tree(fresh_src, destination)

            # 4. Update the version file
            if version_src:
                shutil.copy2(version_src, version_dest)

            self.progress_bar.reset()
            self.status_text.append(f"Update {version} installed. Restarting...")
            QMessageBox.information(
                self, "Update installed",
                f"Version {version} was installed.\n"
                f"A backup of your data is available in:\n{backup_dir}\n\n"
                "The application will restart now.")
            self._restart_application()

        except Exception as e:
            self.progress_bar.reset()
            self.status_text.append(f"Installation Error: {e}")
            QMessageBox.critical(
                self, "Update Error",
                f"Failed to install the update: {e}\n\n"
                f"Your data backup is in: {backup_dir}")

    @Slot(str)
    def on_update_error(self, error_msg):
        self.status_text.append(error_msg)
        QMessageBox.warning(self, "Error", error_msg)
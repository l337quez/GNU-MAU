from mongita import MongitaClientDisk
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                               QWidget, QVBoxLayout, QSystemTrayIcon,
                               QMenu, QListWidget, QScrollArea, QLabel,
                               QDockWidget, QListWidgetItem, QPushButton)
from PySide6.QtGui import QIcon, QAction, QPixmap, QMovie
from PySide6.QtCore import Slot, Qt, QEvent, QTimer
from PySide6.QtWidgets import QSizePolicy
import json, sys, os
from dotenv import load_dotenv
# Mau resources
from about_tab import AboutTab
from setting_tab import SettingTab
from icon import icon
from project_tab import ProjectTab
from project_info_tab import ProjectInfoTab
from project_todo_tab import ProjectTodoTab
from project_note_tab import ProjectNoteTab
from utils import get_resource_path


# load env file
load_dotenv()

# Establecer explícitamente el ID de modelo de usuario de aplicación en Windows
if sys.platform.startswith('win'):
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'CompanyName.ProductName.SubProduct.VersionInformation')

class GIFLabel(QLabel):
    def __init__(self, gif_path):
        super().__init__()
        self.movie_obj = None 
        resolved_path = get_resource_path(gif_path)
        if os.path.exists(resolved_path):
            self.movie_obj = QMovie(resolved_path)
            self.setMovie(self.movie_obj)
            self.movie_obj.start()

        # if os.path.exists(gif_path):
        #     self.movie_obj = QMovie(gif_path)
        #     self.setMovie(self.movie_obj)
        #     self.movie_obj.start()

    def currentPixmap(self):
        if isinstance(self.movie_obj, QMovie) and self.movie_obj.isValid():
            return self.movie_obj.currentPixmap()
        return QPixmap()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GNU Mau")
        self.setGeometry(300, 300, 800, 600)

        # --- CAMBIO 1: Inicializar directorio base storage ---
        self.storage_dir = os.path.join(os.path.dirname(__file__), "storage")
        if not os.path.exists(self.storage_dir):
            try:
                os.makedirs(self.storage_dir)
                print(f"Directorio principal 'storage' creado en: {self.storage_dir}")
            except OSError as e:
                print(f"Error al crear directorio storage: {e}")
        # -----------------------------------------------------

        self.config_path = os.path.join(os.path.expanduser("~"), ".myapp", "config.json")
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        self.config = {}
        self.load_config()

        qp = QPixmap()
        qp.loadFromData(icon)
        appIcon = QIcon(qp)
        self.setWindowIcon(appIcon)

        self.tray_icon = QSystemTrayIcon(appIcon, parent=self)
        self.tray_icon.setToolTip("GNU Mau")
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Quit", self)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.show()

        self.current_project_name = ""
        self.current_project_description = ""
        self.current_project_item = None
        self.current_project_info = {}
        self.current_project_id = "default_project_id" 
        self.db_name = "projects_db"

        print("Connecting to Mongita...")
        mongita_db_dir = os.path.join(os.path.dirname(__file__), "mongita_data")
        os.environ["MONGITA_DIR"] = mongita_db_dir
        self.client = MongitaClientDisk(mongita_db_dir)
        self.db = self.client[self.db_name]
        self.create_collections()

        if self.db.projects.count_documents({}) == 0:
            print("Inserting a test project into Mongita...")
            self.db.projects.insert_one({
                "name": "Demo project",
                "description": "This is a test project.",
                "icon_path": "assets/project_images/default_icon.png"
            })

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.project_tab = ProjectTab(self)
        self.project_info_tab = ProjectInfoTab(self)
        self.project_todo_tab = ProjectTodoTab(self, project_id=self.current_project_id)
        self.project_note_tab = ProjectNoteTab(self)
        self.setting_tab = SettingTab(self)
        self.about_tab = AboutTab(self)
        self.tabs.addTab(self.project_tab, "Project")
        self.tabs.addTab(self.project_info_tab, "Information")
        self.tabs.addTab(self.project_todo_tab, "Todo")
        self.tabs.addTab(self.project_note_tab, "Note")
        self.tabs.addTab(self.setting_tab, "Setting")
        self.tabs.addTab(self.about_tab, "About")

        self.project_list_widget = QListWidget()
        self.project_list_widget.itemClicked.connect(self.display_project_info)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.project_list_widget)

        self.add_create_project_button()

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(scroll_area)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)

        self.dock_widget = QDockWidget("Projects", self)
        self.dock_widget.setWidget(sidebar_widget)
        self.dock_widget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

        self.load_projects()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_gif_icons)
        self.timer.start(100)

        dock_position_int = self.config.get("sidebar_position", Qt.LeftDockWidgetArea.value)
        dock_position = Qt.DockWidgetArea(dock_position_int)
        self.addDockWidget(dock_position, self.dock_widget)

        self.dock_widget.dockLocationChanged.connect(self.save_sidebar_position)

    def save_sidebar_position(self):
        position = self.dockWidgetArea(self.dock_widget)
        self.config["sidebar_position"] = position.value
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def move_sidebar(self, area):
        """
        Move the dock widget to the specified position.
        area: A Qt.DockWidgetArea value (Left, Right, Top, Bottom)
        """
        self.addDockWidget(area, self.dock_widget)

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            dark_mode = self.config.get("dark_mode", False)
            self.apply_theme(dark_mode)

    def apply_theme(self, dark_mode):
        if dark_mode:
            try:
                with open("dark_theme.qss", "r") as f:
                    dark_style_sheet = f.read()
                self.setStyleSheet(dark_style_sheet)
            except FileNotFoundError:
                print("Tema oscuro no encontrado")
        else:
            self.setStyleSheet("")

    def create_collections(self):
        if 'projects' not in self.db.list_collection_names():
            print("Mongita: Colección 'projects' creada automáticamente al primer insert.")
        if 'todos' not in self.db.list_collection_names():
            print("Mongita: Colección 'todos' creada automáticamente al primer insert.")

    def add_create_project_button(self):
        create_project_button = QPushButton("Create Project")
        create_project_button.setStyleSheet("padding: 4px; margin: 8px;")
        size_policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        create_project_button.setSizePolicy(size_policy)
        create_project_button.clicked.connect(self.show_create_project_form)
        
        create_project_item = QListWidgetItem(self.project_list_widget)
        create_project_item.setSizeHint(create_project_button.sizeHint())
        create_project_item.setData(Qt.UserRole, None) 
        self.project_list_widget.setItemWidget(create_project_item, create_project_button)

    def show_create_project_form(self):
        self.current_project_item = None
        self.current_project_name = ""
        self.current_project_description = ""
        self.current_project_info = {}
        self.current_project_id = None 
        self.project_tab.name_input.clear()
        self.project_tab.description_input.clear()
        self.project_tab.clear_table() 
        self.project_tab.set_editing_enabled(True) 
        self.tabs.setCurrentWidget(self.project_tab)

    def load_projects(self):
        self.gif_labels = []
        projects_collection = self.db.projects
        projects = projects_collection.find()
        
        self.project_list_widget.clear()
        self.add_create_project_button() 
        
        for project in projects:
            description = project['description'] if len(project['description']) <= 8 else project['description'][:8] + "..."
            item = QListWidgetItem(f"{project['name']}: {description}")
            
            project_id = str(project["_id"]) 
            item.setData(Qt.UserRole, project_id) 

            # --- CORRECCIÓN 1: Cargar la ruta real de la DB al iniciar ---
            icon_path = project.get('icon_path', "assets/project_images/default_icon.png")
            item.setData(Qt.UserRole + 1, icon_path) 

            project_folder_path = os.path.join(self.storage_dir, project_id)
            if not os.path.exists(project_folder_path):
                try:
                    os.makedirs(project_folder_path)
                except OSError as e:
                    print(f"Error al crear la carpeta: {e}")

            if icon_path.endswith('.gif'):
                gif_label = GIFLabel(icon_path)
                self.gif_labels.append((item, gif_label))
                item.setIcon(QIcon(gif_label.currentPixmap()))
            else:
                item.setIcon(QIcon(icon_path))
            
            item.icon_path = icon_path
            self.project_list_widget.addItem(item)

        if self.project_list_widget.count() > 1:
            first_project_item = self.project_list_widget.item(1)
            self.project_list_widget.setCurrentItem(first_project_item)
            self.display_project_info(first_project_item)

    def update_gif_icons(self):
        for item, gif_label in self.gif_labels:
            try:
                pix = gif_label.currentPixmap()
                if pix and not pix.isNull():
                    item.setIcon(QIcon(pix))
            except Exception:
                continue

    @Slot()
    def display_project_info(self, item):
        project_id = item.data(Qt.UserRole)
        if project_id is None: 
            self.show_create_project_form()
            return 

        project = self.db.projects.find_one({"_id": project_id})
        if not project:
            return

        self.current_project_item = item
        self.current_project_id = project_id
        self.current_project_name = project["name"]
        self.current_project_description = project["description"]
        self.current_project_info = project.get("info", {})

        icon_path = project.get('icon_path', "assets/project_images/default_icon.png")
        item.setData(Qt.UserRole + 1, icon_path)

        self.project_info_tab.update_project_info(
            self.current_project_name,
            self.current_project_description,
            self.current_project_info
        )
        self.project_tab.update_project_form(
            self.current_project_name,
            self.current_project_description
        )

        if icon_path.endswith('.gif'):
            gif_label = GIFLabel(icon_path)
            icon = QIcon(gif_label.currentPixmap())
        else:
            icon = QIcon(icon_path)
        self.current_project_item.setIcon(icon)

        self.project_todo_tab.project_id = self.current_project_id
        self.project_todo_tab.update_project_id(self.current_project_id)
        self.project_note_tab.set_project_id(self.current_project_id)

        self.project_info_tab.clear_search()
        self.project_tab.enable_editing()
        self.tabs.setCurrentWidget(self.project_info_tab)

    @Slot()
    def update_project_icon(self, project_name, icon_path):
        if self.current_project_id:
            for i in range(self.project_list_widget.count()):
                item = self.project_list_widget.item(i)
                if item.data(Qt.UserRole) == self.current_project_id:
                    # --- CORRECCIÓN 3: Actualizar la "mochila" de datos ---
                    item.setData(Qt.UserRole + 1, icon_path)
                    
                    if icon_path.endswith('.gif'):
                        found = False
                        for idx, (existing_item, existing_gif_label) in enumerate(self.gif_labels):
                            if existing_item == item:
                                existing_gif_label = GIFLabel(icon_path) 
                                self.gif_labels[idx] = (item, existing_gif_label)
                                item.setIcon(QIcon(existing_gif_label.currentPixmap()))
                                found = True
                                break
                        if not found: 
                            gif_label = GIFLabel(icon_path)
                            self.gif_labels.append((item, gif_label))
                            item.setIcon(QIcon(gif_label.currentPixmap()))
                    else:
                        item.setIcon(QIcon(icon_path))
                    item.icon_path = icon_path 
                    break

    @Slot()
    def closeEvent(self, event):
        should_minimize = self.config.get("minimize_to_tray", True)

        if should_minimize and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "GNU Mau",
                "The application continues to run in the background.",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore() 
        else:
            self.client.close() 
            event.accept()

    @Slot()
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.tray_icon.showMessage(
                "Minimized to Tray",
                "The application has been minimized to the system tray",
                QSystemTrayIcon.Information,
                2000
            )

    def minimize_to_tray(self):
        self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    def on_exit():
        print("closing application...")
    app.aboutToQuit.connect(on_exit)
    sys.exit(app.exec())
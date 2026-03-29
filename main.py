from mongita import MongitaClientDisk
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                               QWidget, QVBoxLayout, QSystemTrayIcon,
                               QMenu, QListWidget, QScrollArea, QLabel,
                               QDockWidget, QListWidgetItem, QPushButton)
from PySide6.QtGui import QIcon, QAction, QPixmap, QMovie
from PySide6.QtCore import Slot, Qt, QEvent, QTimer
from PySide6.QtWidgets import QSizePolicy, QStackedWidget
import json, sys, os
from bson.objectid import ObjectId
from dotenv import load_dotenv
# Mau resources
from about_tab import AboutTab
from setting_tab import SettingTab
from icon import icon
from project_tab import ProjectTab
from project_info_tab import ProjectInfoTab
from project_todo_tab import ProjectTodoTab
from project_note_tab import ProjectNoteTab
from project_diagram_tab import ProjectDiagramTab
from tools import CurlWrapperTab
from utils import get_resource_path, clean_text_format, is_windows


load_dotenv()

if is_windows():
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

        self.storage_dir = os.path.join(os.path.dirname(__file__), "storage")
        if not os.path.exists(self.storage_dir):
            try:
                os.makedirs(self.storage_dir)
                print(f"Directorio principal 'storage' creado en: {self.storage_dir}")
            except OSError as e:
                print(f"Error al crear directorio storage: {e}")

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

        # Stacked Widget for clean switching
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.tabs)
        
        self.tools_tab = CurlWrapperTab(self)
        self.stacked_widget.addWidget(self.tools_tab)
        
        self.setCentralWidget(self.stacked_widget)
        
        self.project_tab = ProjectTab(self)
        self.project_info_tab = ProjectInfoTab(self)
        self.project_todo_tab = ProjectTodoTab(self, project_id=self.current_project_id)
        self.project_note_tab = ProjectNoteTab(self)
        self.project_diagram_tab = ProjectDiagramTab(self)
        self.setting_tab = SettingTab(self)
        self.about_tab = AboutTab(self)
        
        self.tabs.addTab(self.project_tab, "Project")
        self.tabs.addTab(self.project_info_tab, "Information")
        self.tabs.addTab(self.project_todo_tab, "Todo")
        self.tabs.addTab(self.project_note_tab, "Note")
        self.tabs.addTab(self.project_diagram_tab, "Diagram")
        self.tabs.addTab(self.setting_tab, "Setting")
        self.tabs.addTab(self.about_tab, "About")

        self.project_list_widget = QListWidget()
        self.project_list_widget.itemClicked.connect(self.display_project_info)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.project_list_widget)

        sidebar_layout = QVBoxLayout()
        
        # Tools Button
        self.tools_button = QPushButton("🚀 Tools")
        self.tools_button.setFixedHeight(35)
        self.tools_button.setCursor(Qt.PointingHandCursor)
        self.tools_button.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.tools_button.clicked.connect(self.toggle_tools_view)
        sidebar_layout.addWidget(self.tools_button)
        
        self.create_project_button = QPushButton("➕ Create Project")
        self.create_project_button.setFixedHeight(35)
        self.create_project_button.setCursor(Qt.PointingHandCursor)
        self.create_project_button.setStyleSheet("""
            QPushButton {
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
            }

        """)
        self.create_project_button.clicked.connect(self.show_create_project_form)
        sidebar_layout.addWidget(self.create_project_button)

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
            
            # Use 'theme' key, fallback to 'dark_mode' for backward compatibility
            theme = self.config.get("theme")
            if theme is None:
                dark_mode = self.config.get("dark_mode", False)
                theme = "dark_theme" if dark_mode else "Light Theme"
            
            self.apply_theme(theme)

    def apply_theme(self, theme_name):
        if theme_name == "Light Theme":
            self.setStyleSheet("")
        else:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            qss_file = os.path.join(base_path, "themes", f"{theme_name}.qss")
            try:
                with open(qss_file, "r") as f:
                    self.setStyleSheet(f.read())
            except FileNotFoundError:
                print(f"Tema {theme_name} no encontrado en {qss_file}")

    def create_collections(self):
        if 'projects' not in self.db.list_collection_names():
            print("Mongita: Colección 'projects' creada automáticamente al primer insert.")
        if 'todos' not in self.db.list_collection_names():
            print("Mongita: Colección 'todos' creada automáticamente al primer insert.")
        if 'categories' not in self.db.list_collection_names():
            print("Mongita: Colección 'categories' creada automáticamente al primer insert.")

    def show_create_project_form(self):
        self.current_project_item = None
        self.current_project_name = ""
        self.current_project_description = ""
        self.current_project_info = {}
        self.current_project_id = None 
        self.project_tab.name_input.clear()
        self.project_tab.description_input.clear()
        self.project_tab.clear_table() 
        self.project_tab.change_icon_button.setEnabled(False) 
        self.tabs.setCurrentWidget(self.project_tab)

    def load_projects(self):
        self.gif_labels = []
        projects_collection = self.db.projects
        projects = projects_collection.find()
        
        self.project_list_widget.clear()
        
        for project in projects:
            description = project['description'] if len(project['description']) <= 8 else project['description'][:8] + "..."
            item = QListWidgetItem(f"{project['name']}: {description}")
            
            project_id = str(project["_id"]) 
            item.setData(Qt.UserRole, project_id) 

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
                resolved = get_resource_path(icon_path)
                item.setIcon(QIcon(resolved))
            
            item.icon_path = icon_path
            self.project_list_widget.addItem(item)

        if self.project_list_widget.count() > 0:
            first_project_item = self.project_list_widget.item(0)
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

        # Convert to ObjectId for querying
        try:
            p_id = ObjectId(project_id) if isinstance(project_id, str) else project_id
            project = self.db.projects.find_one({"_id": p_id})
        except Exception as e:
            print(f"Error querying project: {e}")
            project = None

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
            icon = QIcon(get_resource_path(icon_path))
        self.current_project_item.setIcon(icon)

        #self.project_todo_tab.project_id = self.current_project_id
        self.project_todo_tab.update_project_id(self.current_project_id)
        self.project_todo_tab.update_project_id(self.current_project_id)
        self.project_note_tab.set_project_id(self.current_project_id)
        self.project_diagram_tab.set_project_id(self.current_project_id)

        # Sincronizar filtro de categories en Information tab (desde info items)
        info = project.get("info", {})
        categories = sorted({
            v.get("category", "") for v in info.values()
            if isinstance(v, dict) and v.get("category", "")
        })
        self.project_info_tab.update_categories_filter(categories)

        self.project_info_tab.clear_search()
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
                        item.setIcon(QIcon(get_resource_path(icon_path)))
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

    @Slot()
    def toggle_tools_view(self):
        if self.stacked_widget.currentIndex() == 0:
            # Switch to tools
            self.stacked_widget.setCurrentIndex(1)
            self.tools_button.setText("⬅ Regresar")
            self.tools_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 10px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
        else:
            # Switch to projects
            self.stacked_widget.setCurrentIndex(0)
            self.tools_button.setText("🚀 Tools")
            self.tools_button.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 10px;
                }
                QPushButton:hover {
                    background-color: #2c3e50;
                }
            """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    def on_exit():
        print("closing application...")
    app.aboutToQuit.connect(on_exit)
    sys.exit(app.exec())
from mongita import MongitaClientDisk
try:
    from mongita.engines.disk_engine import DiskEngine
    _orig_get_doc = DiskEngine.get_doc

    def _safe_get_doc(self, collection, doc_id):
        try:
            return _orig_get_doc(self, collection, doc_id)
        except AssertionError:
            try:
                loc_idx = self._get_file_attrs(collection)
                loc_idx.pop(str(doc_id), None)
                if hasattr(self, "_cache") and collection in self._cache:
                    self._cache[collection].pop(str(doc_id), None)
            except Exception:
                pass
            return None

    DiskEngine.get_doc = _safe_get_doc
except Exception as e:
    print(f"Mongita safe patch notice: {e}")
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QBoxLayout,
                               QWidget, QVBoxLayout, QHBoxLayout, QSystemTrayIcon,
                               QMenu, QListWidget, QScrollArea, QLabel,
                               QDockWidget, QListWidgetItem, QPushButton, QFrame)
from PySide6.QtGui import QIcon, QAction, QPixmap, QMovie, QFontDatabase, QPainter
from PySide6.QtCore import Slot, Qt, QEvent, QTimer, QSize
from PySide6.QtWidgets import QSizePolicy, QStackedWidget
import sys, os
from bson.objectid import ObjectId
try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional at runtime
    load_dotenv = None
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
from utils import (get_resource_path, clean_text_format, is_windows,
                   get_storage_dir, get_mongita_dir, get_config_path,
                   load_config, save_config, get_theme_stylesheet, get_data_dir, get_fa_icon)
from i18n import tr, set_language


if load_dotenv is not None:
    load_dotenv()

# Tamaño cuadrado uniforme para los controles del rail y sus iconos.
SQUARE_SIZE = 44
ICON_SIZE = 36
ICON_MARGIN = 2


def make_square_pixmap(source, canvas=ICON_SIZE, margin=ICON_MARGIN):
    """
    Centra un pixmap dentro de un lienzo cuadrado transparente sin recortarlo
    ni deformarlo (Qt.KeepAspectRatio + margen interno de respiración).
    """
    if source is None or source.isNull():
        return QPixmap()

    target = QPixmap(canvas, canvas)
    target.fill(Qt.transparent)

    inner = max(1, canvas - margin * 2)
    scaled = source.scaled(inner, inner, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    painter = QPainter(target)
    painter.drawPixmap(
        (canvas - scaled.width()) // 2,
        (canvas - scaled.height()) // 2,
        scaled,
    )
    painter.end()
    return target


def square_icon(source):
    """QIcon cuadrado (36x36) para listas y previews."""
    return QIcon(make_square_pixmap(source, ICON_SIZE, ICON_MARGIN))


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
        else:
            fallback = get_resource_path("assets/project_images/default_icon.png")
            if os.path.exists(fallback):
                self.setPixmap(QPixmap(fallback).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # if os.path.exists(gif_path):
        #     self.movie_obj = QMovie(gif_path)
        #     self.setMovie(self.movie_obj)
        #     self.movie_obj.start()

    def currentPixmap(self):
        if isinstance(self.movie_obj, QMovie) and self.movie_obj.isValid():
            return self.movie_obj.currentPixmap()
        return QPixmap()


class ProjectDockWidget(QDockWidget):
    """
    Sidebar dock widget for Projects.
    Prevents closing or disappearing when detached as a floating window.
    If the close event is triggered, it re-docks itself back to the main window.
    """
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.topLevelChanged.connect(self._on_top_level_changed)

    def _on_top_level_changed(self, floating):
        if floating:
            # Strip close button hint from the floating window decorations
            self.setWindowFlags((self.windowFlags() | Qt.CustomizeWindowHint) & ~Qt.WindowCloseButtonHint)
            self.show()

    def closeEvent(self, event):
        event.ignore()
        if self.isFloating():
            self.setFloating(False)


class Snackbar(QFrame):
    """
    Modern floating snackbar notification displayed centered at the bottom of the window.
    Auto-hides after duration_ms milliseconds.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.94);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 18px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, message: str, duration_ms: int = 2500):
        self.label.setText(message)
        self.adjustSize()
        self.reposition()
        self.raise_()
        self.show()
        self.timer.start(duration_ms)

    def reposition(self):
        if self.parent():
            parent_rect = self.parent().rect()
            x = max(10, (parent_rect.width() - self.width()) // 2)
            y = max(10, parent_rect.height() - self.height() - 25)
            self.move(x, y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GNU Mau")
        self.setGeometry(300, 300, 800, 600)

        self.storage_dir = get_storage_dir()
        print(f"Directorio principal 'storage' usando: {self.storage_dir}")

        self.config_path = get_config_path()
        self.config = load_config()
        set_language(self.config.get("language", "en"))

        self.setWindowTitle(self.config.get("window_title") or "GNU Mau")
        geometry = self.config.get("window_geometry")
        if isinstance(geometry, (list, tuple)) and len(geometry) == 4:
            try:
                self.setGeometry(*(int(value) for value in geometry))
            except (TypeError, ValueError):
                print(f"window_geometry inválida en la configuración: {geometry}")

        self.apply_theme(self.config.get("theme", "Light Theme"))

        qp = QPixmap()
        qp.loadFromData(icon)
        appIcon = QIcon(qp)
        self.setWindowIcon(appIcon)

        # System tray support depends on the desktop environment. In headless
        # containers or sessions without a StatusNotifier host it is not
        # available: in that case closing the window must quit the app.
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray_icon = None
        if self.tray_available:
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
        else:
            print("System tray not available: the app will close instead of minimizing.")

        self.current_project_name = ""
        self.current_project_description = ""
        self.current_project_item = None
        self.current_project_info = {}
        self.current_project_id = "default_project_id" 
        self.db_name = self.config.get("db_name", "projects_db")

        print("Connecting to Mongita...")
        mongita_db_dir = get_mongita_dir()
        print(f"Mongita data dir: {mongita_db_dir}")
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
        
        self.stacked_widget.addWidget(self.setting_tab)
        self.stacked_widget.addWidget(self.about_tab)

        self.tabs.addTab(self.project_tab, tr("tab_project"))
        self.tabs.addTab(self.project_info_tab, tr("tab_information"))
        self.tabs.addTab(self.project_todo_tab, tr("tab_todo"))
        self.tabs.addTab(self.project_note_tab, tr("tab_note"))
        self.tabs.addTab(self.project_diagram_tab, tr("tab_diagram"))
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.project_list_widget = QListWidget()
        self.project_list_widget.setIconSize(QSize(28, 28))
        self.project_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_list_widget.setFrameShape(QFrame.NoFrame)
        self.project_list_widget.itemClicked.connect(self.display_project_info)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.project_list_widget)

        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.setContentsMargins(6, 6, 6, 6)
        self.sidebar_layout.setSpacing(6)
        
        # Header con título del sidebar y botón de colapso
        self.sidebar_header_widget = QWidget()
        sidebar_header_layout = QHBoxLayout()
        sidebar_header_layout.setContentsMargins(4, 2, 4, 2)
        sidebar_header_layout.setSpacing(4)

        self.sidebar_title_label = QLabel(tr("projects_dock"))
        self.sidebar_title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #888888;")

        self.sidebar_toggle_button = QPushButton()
        self.sidebar_toggle_button.setFixedSize(26, 26)
        self.sidebar_toggle_button.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle_button.setToolTip(tr("collapse_sidebar"))
        self.sidebar_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.25);
                border: 1px solid rgba(128, 128, 128, 0.4);
            }
        """)
        self.sidebar_toggle_button.setIcon(get_fa_icon("chevron-left", color="#9cdcfe", size=14))
        self.sidebar_toggle_button.clicked.connect(self.toggle_sidebar_collapsed)

        sidebar_header_layout.addWidget(self.sidebar_title_label)
        sidebar_header_layout.addStretch()
        sidebar_header_layout.addWidget(self.sidebar_toggle_button)
        self.sidebar_header_widget.setLayout(sidebar_header_layout)
        self.sidebar_layout.addWidget(self.sidebar_header_widget)

        # Tools Button
        self.tools_button = QPushButton(tr("tools_btn"))
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
        self.tools_button.hide()
        
        self.create_project_button = QPushButton(tr("create_project"))
        self.create_project_button.setFixedHeight(35)
        self.create_project_button.setCursor(Qt.PointingHandCursor)
        self.create_project_button.setToolTip(tr("create_project"))
        self.create_project_button.setStyleSheet("""
            QPushButton {
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 4px;
            }
        """)
        self.create_project_button.clicked.connect(self.show_create_project_form)
        self.sidebar_layout.addWidget(self.create_project_button)

        self.sidebar_layout.addWidget(self.scroll_area, 1)

        # Footer con botones globales de Settings y About
        self.footer_widget = QWidget()
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 4, 0, 0)
        self.footer_layout.setSpacing(6)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(48, 40)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setToolTip(tr("settings_tooltip"))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(128, 128, 128, 0.35);
                border-radius: 8px;
                font-size: 22px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.25);
                border-color: rgba(128, 128, 128, 0.6);
            }
        """)
        self.settings_btn.clicked.connect(self.show_settings_view)

        self.about_btn = QPushButton("ℹ️")
        self.about_btn.setFixedSize(48, 40)
        self.about_btn.setCursor(Qt.PointingHandCursor)
        self.about_btn.setToolTip(tr("about_tooltip"))
        self.about_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(128, 128, 128, 0.35);
                border-radius: 8px;
                font-size: 22px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.25);
                border-color: rgba(128, 128, 128, 0.6);
            }
        """)
        self.about_btn.clicked.connect(self.show_about_view)

        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.settings_btn)
        self.footer_layout.addWidget(self.about_btn)
        self.footer_layout.addStretch()
        self.footer_widget.setLayout(self.footer_layout)
        self.sidebar_layout.addWidget(self.footer_widget)

        self.sidebar_widget = QWidget()
        self.sidebar_widget.setLayout(self.sidebar_layout)

        self.dock_widget = ProjectDockWidget(tr("projects_dock"), self)
        self.dock_empty_title_bar = QWidget()
        self.dock_widget.setTitleBarWidget(self.dock_empty_title_bar)
        self.dock_widget.setWidget(self.sidebar_widget)
        self.dock_widget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

        # Estado del colapso del sidebar
        self.is_sidebar_collapsed = self.config.get("sidebar_collapsed", False)
        self.saved_expanded_width = 250

        self.load_projects()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_gif_icons)
        self.timer.start(100)

        dock_position_int = self.config.get("sidebar_position", Qt.LeftDockWidgetArea.value)
        dock_position = Qt.DockWidgetArea(dock_position_int)
        self.addDockWidget(dock_position, self.dock_widget)

        self.dock_widget.dockLocationChanged.connect(self.save_sidebar_position)

        # Aplicar estado inicial de colapso si estaba guardado
        if self.is_sidebar_collapsed:
            self._apply_collapsed_ui(True)

        # Snackbar flotante centralizado para mensajes de acción
        self.snackbar = Snackbar(self)
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().messageChanged.connect(self._on_status_bar_message)
            self.statusBar().hide()

    def _on_status_bar_message(self, message):
        if message:
            self.show_snackbar(message)

    def show_snackbar(self, message: str, duration_ms: int = 2500):
        if hasattr(self, "snackbar"):
            self.snackbar.show_message(message, duration_ms)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "snackbar") and self.snackbar.isVisible():
            self.snackbar.reposition()

    def toggle_sidebar_collapsed(self):
        """Alternar entre sidebar expandido y colapsado (compact rail)."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        self.config = save_config({"sidebar_collapsed": self.is_sidebar_collapsed})
        self._apply_collapsed_ui(self.is_sidebar_collapsed)

    def _apply_collapsed_ui(self, collapsed):
        """Actualiza la apariencia y el ancho del sidebar según el estado."""
        if collapsed:
            current_w = self.dock_widget.width()
            if current_w > 70:
                self.saved_expanded_width = current_w

            self.sidebar_title_label.hide()
            self.sidebar_toggle_button.setIcon(get_fa_icon("chevron-right", color="#9cdcfe", size=14))
            self.sidebar_toggle_button.setToolTip(tr("expand_sidebar"))

            # Rail compacto: los 3 botones comparten tamaño, radio y estados.
            button_size = SQUARE_SIZE
            accent_color = "#9cdcfe"

            self.create_project_button.setText("")
            self.create_project_button.setIcon(get_fa_icon("plus", color="#ffffff", size=20))
            self.create_project_button.setIconSize(QSize(20, 20))
            self.create_project_button.setFixedSize(button_size, button_size)
            self.create_project_button.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    border: 1px solid #2c3e50;
                    border-radius: 6px;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #2c3e50;
                }
            """)
            self.sidebar_layout.setAlignment(self.create_project_button, Qt.AlignHCenter)

            compact_icon_style = """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid rgba(128, 128, 128, 0.35);
                    border-radius: 6px;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.25);
                    border-color: rgba(128, 128, 128, 0.6);
                }
            """

            self.settings_btn.setText("")
            self.settings_btn.setIcon(get_fa_icon("gear", color=accent_color, size=20))
            self.settings_btn.setIconSize(QSize(20, 20))
            self.settings_btn.setFixedSize(button_size, button_size)
            self.settings_btn.setStyleSheet(compact_icon_style)

            self.about_btn.setText("")
            self.about_btn.setIcon(get_fa_icon("circle-info", color=accent_color, size=20))
            self.about_btn.setIconSize(QSize(20, 20))
            self.about_btn.setFixedSize(button_size, button_size)
            self.about_btn.setStyleSheet(compact_icon_style)

            # Footer vertical compacto con los iconos centrados
            for i in reversed(range(self.footer_layout.count())):
                self.footer_layout.takeAt(i)
            self.footer_layout.setContentsMargins(0, 4, 0, 0)
            self.footer_layout.setSpacing(6)
            self.footer_layout.setDirection(QBoxLayout.TopToBottom)
            self.footer_layout.setAlignment(Qt.AlignHCenter)
            self.footer_layout.addWidget(self.settings_btn, 0, Qt.AlignHCenter)
            self.footer_layout.addWidget(self.about_btn, 0, Qt.AlignHCenter)

            # Ocultar texto en items de lista
            for i in range(self.project_list_widget.count()):
                item = self.project_list_widget.item(i)
                full_text = item.data(Qt.UserRole + 2)
                if not full_text:
                    full_text = item.text()
                    item.setData(Qt.UserRole + 2, full_text)
                item.setText("")
                item.setToolTip(full_text)

            # Modo icono en una sola columna para centrar los iconos del rail
            self.project_list_widget.setViewMode(QListWidget.IconMode)
            self.project_list_widget.setFlow(QListWidget.TopToBottom)
            self.project_list_widget.setWrapping(False)
            self.project_list_widget.setMovement(QListWidget.Static)
            self.project_list_widget.setResizeMode(QListWidget.Adjust)
            self.project_list_widget.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            self.project_list_widget.setGridSize(QSize(SQUARE_SIZE, SQUARE_SIZE))
            self.project_list_widget.setStyleSheet("""
                QListWidget {
                    background: transparent;
                    border: none;
                }
                QListWidget::item {
                    width: 44px;
                    height: 44px;
                    margin: 2px 0px;
                    padding: 0px;
                    border: none;
                    border-bottom: none;
                    color: transparent;
                }
                QListWidget::item:selected {
                    background: rgba(128, 128, 128, 0.35);
                    border-radius: 6px;
                    border: none;
                    border-bottom: none;
                    color: transparent;
                }
                QListWidget::item:hover {
                    background: rgba(128, 128, 128, 0.2);
                    border-radius: 6px;
                    border: none;
                    border-bottom: none;
                    color: transparent;
                }
                QListWidget QScrollBar:vertical {
                    width: 4px;
                    background: transparent;
                }
                QListWidget QScrollBar::handle:vertical {
                    background: rgba(128, 128, 128, 0.5);
                    border-radius: 2px;
                    min-height: 20px;
                }
                QListWidget QScrollBar::add-line:vertical,
                QListWidget QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Ancho simétrico y sin scroll horizontal
            self.project_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.sidebar_layout.setContentsMargins(4, 4, 4, 4)
            self.sidebar_layout.setSpacing(6)
            self.dock_widget.setMinimumWidth(52)
            self.dock_widget.setMaximumWidth(52)
            self.resizeDocks([self.dock_widget], [52], Qt.Horizontal)
        else:
            self.sidebar_title_label.show()
            self.sidebar_toggle_button.setIcon(get_fa_icon("chevron-left", color="#9cdcfe", size=14))
            self.sidebar_toggle_button.setToolTip(tr("collapse_sidebar"))

            # Botón crear proyecto expandido (texto y ancho completo)
            self.create_project_button.setIcon(QIcon())
            self.create_project_button.setText(tr("create_project"))
            self.create_project_button.setMinimumWidth(0)
            self.create_project_button.setMaximumWidth(16777215)
            self.create_project_button.setFixedHeight(35)
            self.create_project_button.setStyleSheet("""
                QPushButton {
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 4px;
                }
            """)

            # Footer horizontal con el estilo expandido original
            self.settings_btn.setIcon(QIcon())
            self.settings_btn.setText("⚙️")
            self.settings_btn.setFixedSize(48, 40)
            self.settings_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid rgba(128, 128, 128, 0.35);
                    border-radius: 8px;
                    font-size: 22px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.25);
                    border-color: rgba(128, 128, 128, 0.6);
                }
            """)

            self.about_btn.setIcon(QIcon())
            self.about_btn.setText("ℹ️")
            self.about_btn.setFixedSize(48, 40)
            self.about_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid rgba(128, 128, 128, 0.35);
                    border-radius: 8px;
                    font-size: 22px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.25);
                    border-color: rgba(128, 128, 128, 0.6);
                }
            """)

            for i in reversed(range(self.footer_layout.count())):
                self.footer_layout.takeAt(i)
            self.footer_layout.setContentsMargins(0, 4, 0, 0)
            self.footer_layout.setSpacing(6)
            self.footer_layout.setDirection(QBoxLayout.LeftToRight)
            self.footer_layout.setAlignment(Qt.AlignCenter)
            self.footer_layout.addStretch()
            self.footer_layout.addWidget(self.settings_btn)
            self.footer_layout.addWidget(self.about_btn)
            self.footer_layout.addStretch()

            # Restaurar texto de items
            for i in range(self.project_list_widget.count()):
                item = self.project_list_widget.item(i)
                full_text = item.data(Qt.UserRole + 2)
                if full_text:
                    item.setText(full_text)

            # Volver a la lista normal
            self.project_list_widget.setViewMode(QListWidget.ListMode)
            self.project_list_widget.setFlow(QListWidget.TopToBottom)
            self.project_list_widget.setWrapping(True)
            self.project_list_widget.setMovement(QListWidget.Static)
            self.project_list_widget.setResizeMode(QListWidget.Fixed)
            self.project_list_widget.setGridSize(QSize())
            self.project_list_widget.setIconSize(QSize(28, 28))
            self.project_list_widget.setStyleSheet("")

            self.sidebar_layout.setContentsMargins(6, 6, 6, 6)
            self.sidebar_layout.setSpacing(6)
            self.dock_widget.setMinimumWidth(160)
            self.dock_widget.setMaximumWidth(524287)
            expanded_w = max(self.saved_expanded_width, 220)
            self.resizeDocks([self.dock_widget], [expanded_w], Qt.Horizontal)

    def save_sidebar_position(self):
        position = self.dockWidgetArea(self.dock_widget)
        self.config = save_config({"sidebar_position": position.value})

    def move_sidebar(self, area):
        """
        Move the dock widget to the specified position.
        area: A Qt.DockWidgetArea value (Left, Right, Top, Bottom)
        """
        self.addDockWidget(area, self.dock_widget)

    def apply_theme(self, theme_name):
        """
        Apply a theme to the whole application.
        Returns False when the QSS file for the theme is missing.
        """
        stylesheet = get_theme_stylesheet(theme_name)
        if stylesheet is None:
            return False
        self.setStyleSheet(stylesheet)
        return True

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
        self.project_tab.reset_icon_preview()
        self.stacked_widget.setCurrentWidget(self.tabs)
        self.tabs.setCurrentWidget(self.project_tab)

    @Slot()
    def show_settings_view(self):
        self.stacked_widget.setCurrentWidget(self.setting_tab)

    @Slot()
    def show_about_view(self):
        self.stacked_widget.setCurrentWidget(self.about_tab)

    @Slot()
    def show_project_tabs_view(self):
        self.stacked_widget.setCurrentWidget(self.tabs)

    def retranslate_ui(self):
        self.dock_widget.setWindowTitle(tr("projects_dock"))
        self.sidebar_title_label.setText(tr("projects_dock"))
        if not getattr(self, "is_sidebar_collapsed", False):
            self.create_project_button.setText(tr("create_project"))
            self.sidebar_toggle_button.setToolTip(tr("collapse_sidebar"))
        else:
            self.sidebar_toggle_button.setToolTip(tr("expand_sidebar"))
        self.tools_button.setText(tr("tools_btn"))
        self.settings_btn.setToolTip(tr("settings_tooltip"))
        self.about_btn.setToolTip(tr("about_tooltip"))

        # Update tabs
        self.tabs.setTabText(0, tr("tab_project"))
        self.tabs.setTabText(1, tr("tab_information"))
        self.tabs.setTabText(2, tr("tab_todo"))
        self.tabs.setTabText(3, tr("tab_note"))
        self.tabs.setTabText(4, tr("tab_diagram"))

        # Retranslate child tabs
        if hasattr(self, "project_tab") and hasattr(self.project_tab, "retranslate_ui"):
            self.project_tab.retranslate_ui()
        if hasattr(self, "project_todo_tab") and hasattr(self.project_todo_tab, "retranslate_ui"):
            self.project_todo_tab.retranslate_ui()
        if hasattr(self, "setting_tab") and hasattr(self.setting_tab, "retranslate_ui"):
            self.setting_tab.retranslate_ui()
        if hasattr(self, "about_tab") and hasattr(self.about_tab, "retranslate_ui"):
            self.about_tab.retranslate_ui()

    def load_projects(self):
        self.gif_labels = []
        projects_collection = self.db.projects
        projects = projects_collection.find()
        
        self.project_list_widget.clear()
        
        for project in projects:
            desc = project.get('description', '').strip()
            # Truncado elegante y completo con tooltip
            if len(desc) > 30:
                short_desc = desc[:28] + "..."
            else:
                short_desc = desc
            display_text = f"{project['name']}: {short_desc}" if short_desc else project['name']
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole + 2, display_text)
            item.setToolTip(f"{project['name']}\n{desc}" if desc else project['name'])
            if getattr(self, "is_sidebar_collapsed", False):
                item.setText("")
            
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
                item.setIcon(square_icon(gif_label.currentPixmap()))
            else:
                resolved = get_resource_path(icon_path)
                item.setIcon(square_icon(QPixmap(resolved)))
            
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
                    item.setIcon(square_icon(pix))
            except Exception:
                continue

    @Slot(int)
    def on_tab_changed(self, index):
        # Si se cambia a la pestaña de Todo (index 2), recargar la lista de tareas
        if index == 2 and hasattr(self, "project_todo_tab") and self.current_project_id:
            try:
                if hasattr(self.project_todo_tab, "view_stack") and self.project_todo_tab.view_stack.currentIndex() == 1:
                    self.project_todo_tab.kanban_board.refresh_board()
                else:
                    self.project_todo_tab.load_todos()
            except Exception as e:
                print(f"Error recargando todos en cambio de tab: {e}")

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

        self.stacked_widget.setCurrentWidget(self.tabs)
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
                                item.setIcon(square_icon(existing_gif_label.currentPixmap()))
                                found = True
                                break
                        if not found: 
                            gif_label = GIFLabel(icon_path)
                            self.gif_labels.append((item, gif_label))
                            item.setIcon(square_icon(gif_label.currentPixmap()))
                    else:
                        item.setIcon(square_icon(QPixmap(get_resource_path(icon_path))))
                    item.icon_path = icon_path 
                    break

    @Slot()
    def closeEvent(self, event):
        should_minimize = self.config.get("minimize_to_tray", True)
        tray_usable = self.tray_available and self.tray_icon is not None and self.tray_icon.isVisible()

        if should_minimize and tray_usable:
            self.hide()
            self.tray_icon.showMessage(
                "GNU Mau",
                "The application continues to run in the background.",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            try:
                self.client.close()
            except Exception as e:
                print(f"Error closing the database: {e}")
            event.accept()
            # Make sure the process ends even when the tray is unavailable
            QApplication.quit()

    @Slot()
    def changeEvent(self, event):
        if (event.type() == QEvent.WindowStateChange and self.isMinimized()
                and self.tray_available and self.tray_icon is not None):
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
    emoji_font = get_resource_path("assets/fonts/NotoColorEmoji.ttf")
    if os.path.exists(emoji_font):
        font_id = QFontDatabase.addApplicationFont(emoji_font)
        if font_id != -1:
            print("Loaded bundled emoji font:", QFontDatabase.applicationFontFamilies(font_id))
    window = MainWindow()
    window.show()
    def on_exit():
        print("closing application...")
    app.aboutToQuit.connect(on_exit)
    sys.exit(app.exec())
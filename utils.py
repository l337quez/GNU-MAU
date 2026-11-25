import sys, os, subprocess, webbrowser
import json
from PySide6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat 

# Optional dotenv import so the app can start even if python-dotenv
# is not yet installed in the active environment.
try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # Handled in main.py


def is_windows():
    return sys.platform.startswith('win')


def is_macos():
    return sys.platform == 'darwin'


def is_linux():
    return sys.platform.startswith('linux')


def get_app_dir():
    """
    Writable directory of the application (next to the executable when frozen,
    the source directory otherwise).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_base():
    """
    Directory that holds read-only resources (assets, themes).
    Inside a PyInstaller bundle resources live in sys._MEIPASS; when running
    from source they are next to this file, never relative to the CWD.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller and
    independent from the current working directory.
    """
    if not relative_path:
        return ""
    norm_path = relative_path.replace("\\", "/")
    if "assets/" in norm_path:
        relative_path = "assets/" + norm_path.split("assets/", 1)[1]

    # 1. Check resource base (sys._MEIPASS or source directory)
    cand = os.path.join(get_resource_base(), relative_path)
    if os.path.exists(cand):
        return cand

    # 2. Check next to executable or in _internal
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        direct = os.path.join(exe_dir, relative_path)
        if os.path.exists(direct):
            return direct
        internal = os.path.join(exe_dir, "_internal", relative_path)
        if os.path.exists(internal):
            return internal

    return cand


def get_fa_icon(name, color="#888888", size=20):
    """
    Renders a Font Awesome solid SVG icon to a QIcon with the specified color and size.
    """
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
    from PySide6.QtSvg import QSvgRenderer

    relative_svg = os.path.join("fontawesome-free-6.5.2-desktop", "svgs", "solid", f"{name}.svg")
    svg_path = get_resource_path(relative_svg)

    if not os.path.exists(svg_path):
        return QIcon()

    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        # Inyectar fill con el color deseado
        if "<svg " in svg_content:
            svg_content = svg_content.replace("<svg ", f'<svg fill="{color}" ', 1)

        renderer = QSvgRenderer(svg_content.encode("utf-8"))
        pix = QPixmap(size, size)
        pix.fill(QColor("transparent"))
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return QIcon(pix)
    except Exception as e:
        print(f"Error cargando icono Font Awesome {name}: {e}")
        return QIcon()


def get_data_dir(folder_name=None):
    """
    Base directory for user data (storage + mongita_data).
    GNU_MAU_DATA_DIR allows mounting a persistent volume (Podman/Docker).

    For PyInstaller onedir builds the historical location is ``_internal``
    (next to the executable), so existing installations keep their data.
    """
    custom = os.environ.get("GNU_MAU_DATA_DIR")
    if custom:
        base = os.path.abspath(os.path.expanduser(custom))
    elif getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        internal_dir = os.path.join(exe_dir, "_internal")
        base = internal_dir if os.path.isdir(internal_dir) else exe_dir
    else:
        base = get_app_dir()
    
    if folder_name:
        target = os.path.join(base, folder_name)
        os.makedirs(target, exist_ok=True)
        return target
    return base


def get_storage_dir():
    target = os.path.join(get_data_dir(), "storage")
    os.makedirs(target, exist_ok=True)
    return target


def get_mongita_dir():
    target = os.path.join(get_data_dir(), "mongita_data")
    os.makedirs(target, exist_ok=True)
    return target


def get_config_dir():
    """
    Directory for the persistent configuration.
    GNU_MAU_CONFIG_DIR allows mounting a persistent volume (Podman/Docker).
    """
    custom = os.environ.get("GNU_MAU_CONFIG_DIR")
    if custom:
        return os.path.abspath(os.path.expanduser(custom))
    return os.path.join(os.path.expanduser("~"), ".myapp")


def get_config_path():
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")


def ensure_dir(path):
    """Create a directory (and parents) if it does not exist."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError as e:
        print(f"Error creating directory {path}: {e}")
        return False


def normalize_theme(theme_name):
    """
    Normalize theme names so legacy configurations ('dark_theme.qss',
    'Dark Theme', 'dark_theme') map to the canonical file basename ('dark_theme').
    """
    if not theme_name:
        return "light_theme"

    name = str(theme_name).strip()
    if name.lower().endswith(".qss"):
        name = name[:-4]

    canonical = {
        "arctic mist": "arctic_mist",
        "arctic_mist": "arctic_mist",
        "amber dusk": "amber_dusk",
        "amber_dusk": "amber_dusk",
        "dark theme": "dark_theme",
        "dark_theme": "dark_theme",
        "light theme": "light_theme",
        "light_theme": "light_theme",
        "solarized light": "solarized_light",
        "solarized_light": "solarized_light",
        "tokyo night": "tokyo_night",
        "tokyo_night": "tokyo_night",
    }
    return canonical.get(name.lower(), name)


def load_config():
    """Load configuration from disk with safe defaults."""
    defaults = {
        "theme": "light_theme",
        "minimize_to_tray": True,
        "enable_ai_integration": True,
        "sidebar_position": 1,
        "sidebar_collapsed": False,
        "db_name": "projects_db",
        "language": "en",
    }
    path = get_config_path()
    if not os.path.exists(path):
        return defaults

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return defaults

            # Migrate legacy boolean flag
            if "dark_mode" in data and "theme" not in data:
                data["theme"] = "dark_theme" if data.get("dark_mode") else "light_theme"

            # Migrate legacy display name
            if "theme_text" in data and "theme" not in data:
                data["theme"] = normalize_theme(data.get("theme_text"))
            elif "theme" in data:
                data["theme"] = normalize_theme(data.get("theme"))

            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        print(f"Error loading config from {path}: {e}")
        return defaults


def save_config(updates):
    """
    Update configuration keys and persist to disk.
    Always normalizes the theme name if provided.
    """
    current = load_config()
    current.update(updates)
    if "theme" in current:
        current["theme"] = normalize_theme(current["theme"])

    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
    except Exception as e:
        print(f"Error saving config to {path}: {e}")
    return current


def get_theme_stylesheet(theme_name):
    """
    Load a QSS stylesheet by canonical theme name.
    Returns the CSS string or empty string on failure.
    """
    canonical = normalize_theme(theme_name)
    if canonical == "light_theme":
        return ""

    qss_path = get_resource_path(os.path.join("themes", f"{canonical}.qss"))
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"Theme '{theme_name}' not found at {qss_path}: {e}")
        return ""


def make_relative_path(absolute_path):
    """
    Converts an absolute path to a relative path if the file is inside
    the program's base directory. Otherwise returns the absolute path unchanged.
    This ensures icon paths stored in the DB are portable when moving the app folder.
    """
    base_path = get_app_dir()

    try:
        relative = os.path.relpath(absolute_path, base_path)
        if not relative.startswith('..'):
            return relative.replace('\\', '/')
    except ValueError:
        pass

    return absolute_path


def open_system_terminal(command):
    """
    Opens the system's default terminal and executes the command.
    Returns True when a terminal was launched, False otherwise.
    """
    try:
        if is_windows():
            subprocess.Popen(f'start cmd /k "{command}"', shell=True)
            return True

        if is_macos():
            escaped = command.replace('"', '\\"')
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "{escaped}" activate'
            ])
            return True

        # Linux: try common terminal emulators
        terminals = [
            ["x-terminal-emulator", "-e", f"bash -c '{command}; exec bash'"],
            ["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"],
            ["konsole", "-e", "bash", "-c", f"{command}; exec bash"],
            ["xfce4-terminal", "-e", f"bash -c '{command}; exec bash'"],
            ["alacritty", "-e", "bash", "-c", f"{command}; exec bash"],
            ["kitty", "bash", "-c", f"{command}; exec bash"],
            ["xterm", "-e", f"bash -c '{command}; exec bash'"],
        ]
        for term_cmd in terminals:
            try:
                subprocess.Popen(term_cmd)
                return True
            except FileNotFoundError:
                continue
        return False
    except Exception as e:
        print(f"Failed to launch system terminal: {e}")
        return False


def open_browser(url):
    """
    Opens the default web browser with the given URL.
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        webbrowser.open(url)
    except Exception as e:
        print(f"Error opening browser: {e}")


def clean_text_format(editor_or_cursor, on_after_clean=None):
    """
    Remove rich text formatting (background colors, fonts)
    and leave only plain text.
    Handles both a QTextEdit/QPlainTextEdit widget or a QTextCursor.
    """
    if hasattr(editor_or_cursor, "textCursor"):
        cursor = editor_or_cursor.textCursor()
        editor = editor_or_cursor
    else:
        cursor = editor_or_cursor
        editor = None

    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.Document)
    
    if cursor.hasSelection():
        text_puro = cursor.selectedText().replace('\u2029', '\n')
        
        clean_char_fmt = QTextCharFormat() 
        clean_block_fmt = QTextBlockFormat()

        cursor.setBlockFormat(clean_block_fmt)
        cursor.setCharFormat(clean_char_fmt)
        cursor.insertText(text_puro, clean_char_fmt)
        
        if editor and hasattr(editor, "setFocus"):
            editor.setFocus()
        
        if on_after_clean and callable(on_after_clean):
            on_after_clean()


def patch_mongita():
    """
    Sincroniza y protege Mongita contra condiciones de carrera multi-proceso
    (p. ej., cuando la IA o scripts externos crean tareas mientras GNU Mau está abierto).
    """
    try:
        import bson
        from mongita.engines import disk_engine
        itrn = sys.intern

        orig_put_metadata = disk_engine.DiskEngine.put_metadata

        def patched_get_file_attrs(self, collection):
            file_attrs_path = self._get_full_path(collection, "$.file_attrs")
            mtime = os.path.getmtime(file_attrs_path) if os.path.exists(file_attrs_path) else 0
            cached_mtime = getattr(self, "_file_attrs_mtime", {}).get(collection, -1)
            if collection not in self._file_attrs or mtime != cached_mtime:
                try:
                    with open(file_attrs_path, "rb") as f:
                        disk_attrs = bson.decode(f.read())
                except FileNotFoundError:
                    disk_attrs = {"loc_idx": {}, "spare_bytes": 0, "total_bytes": 0}
                if collection in self._file_attrs:
                    mem_loc = self._file_attrs[collection].setdefault("loc_idx", {})
                    for k, v in disk_attrs.get("loc_idx", {}).items():
                        if k not in mem_loc:
                            mem_loc[k] = v
                    for k in list(mem_loc.keys()):
                        if k not in disk_attrs.get("loc_idx", {}):
                            mem_loc.pop(k, None)
                    self._file_attrs[collection]["spare_bytes"] = disk_attrs.get("spare_bytes", 0)
                    self._file_attrs[collection]["total_bytes"] = disk_attrs.get("total_bytes", 0)
                else:
                    self._file_attrs[itrn(collection)] = disk_attrs
                if hasattr(self, "_cache") and itrn(collection) in self._cache:
                    self._cache[itrn(collection)].clear()
                if not hasattr(self, "_file_attrs_mtime"):
                    self._file_attrs_mtime = {}
                self._file_attrs_mtime[collection] = mtime
            return self._file_attrs[collection]["loc_idx"]

        def patched_put_metadata(self, collection, metadata):
            file_attrs_path = self._get_full_path(collection, "$.file_attrs")
            if os.path.exists(file_attrs_path):
                try:
                    with open(file_attrs_path, "rb") as f:
                        disk_attrs = bson.decode(f.read())
                    mem_loc = self._file_attrs.setdefault(collection, {"total_bytes": 0, "spare_bytes": 0, "loc_idx": {}}).setdefault("loc_idx", {})
                    for k, v in disk_attrs.get("loc_idx", {}).items():
                        if k not in mem_loc:
                            mem_loc[k] = v
                except Exception:
                    pass
            ret = orig_put_metadata(self, collection, metadata)
            if hasattr(self, "_file_attrs_mtime") and os.path.exists(file_attrs_path):
                try:
                    self._file_attrs_mtime[collection] = os.path.getmtime(file_attrs_path)
                except Exception:
                    pass
            return ret

        disk_engine.DiskEngine._get_file_attrs = patched_get_file_attrs
        disk_engine.DiskEngine.put_metadata = patched_put_metadata
    except Exception as e:
        print(f"Aviso: No se pudo aplicar el parche multi-proceso de Mongita: {e}")


# Aplicar el parche automáticamente al importar utils
patch_mongita()


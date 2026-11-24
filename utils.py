import json
import os
import shutil
import subprocess
import sys
import webbrowser

from PySide6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat

APP_NAME = "GNU Mau"

# Default application configuration. Any value missing from the user's
# config.json is completed from here so the rest of the code can rely on it.
DEFAULT_CONFIG = {
    "theme": "Light Theme",
    "db_name": "projects_db",
    "window_title": APP_NAME,
    "window_geometry": [300, 300, 800, 600],
    "sidebar_position": 1,  # Qt.LeftDockWidgetArea
    "minimize_to_tray": True,
}

# Accepted theme spellings (legacy configs used "Dark Theme" or "theme_text").
THEME_ALIASES = {
    "dark": "dark_theme",
    "dark_theme": "dark_theme",
    "Dark Theme": "dark_theme",
    "light": "Light Theme",
    "light_theme": "Light Theme",
    "Light": "Light Theme",
    "Light Theme": "Light Theme",
    "arctic_mist": "arctic_mist",
    "Arctic Mist": "arctic_mist",
    "amber_dusk": "amber_dusk",
    "Amber Dusk": "amber_dusk",
}


def is_windows():
    return sys.platform.startswith('win')


def is_macos():
    return sys.platform == 'darwin'


def is_linux():
    return sys.platform.startswith('linux')


def get_resource_base():
    """
    Directory that holds read-only resources (assets, themes).
    Inside a PyInstaller bundle resources live in sys._MEIPASS; when running
    from source they are next to this file, never relative to the CWD.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def get_app_dir():
    """
    Writable directory of the application (next to the executable when frozen,
    the source directory otherwise).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller and
    independent from the current working directory.
    """
    return os.path.join(get_resource_base(), relative_path)


def get_data_dir():
    """
    Base directory for user data (storage + mongita_data).
    GNU_MAU_DATA_DIR allows mounting a persistent volume (Podman/Docker).

    For PyInstaller onedir builds the historical location is ``_internal``
    (next to the executable), so existing installations keep their data.
    """
    custom = os.environ.get("GNU_MAU_DATA_DIR")
    if custom:
        return os.path.abspath(os.path.expanduser(custom))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        internal_dir = os.path.join(exe_dir, "_internal")
        return internal_dir if os.path.isdir(internal_dir) else exe_dir
    return get_app_dir()


def get_storage_dir():
    return os.path.join(get_data_dir(), "storage")


def get_mongita_dir():
    return os.path.join(get_data_dir(), "mongita_data")


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
        print(f"Error al crear el directorio {path}: {e}")
        return False


def normalize_theme(theme_name):
    """Return the internal theme name (file name without .qss)."""
    if not theme_name:
        return "Light Theme"
    return THEME_ALIASES.get(str(theme_name).strip(), str(theme_name).strip())


def normalize_config(config):
    """
    Merge a raw config with the defaults, dropping obsolete keys and
    migrating the old ``dark_mode`` flag to the canonical ``theme`` key.
    """
    cfg = dict(DEFAULT_CONFIG)
    raw_theme = None
    if isinstance(config, dict):
        raw_theme = config.get("theme")
        cfg.update(config)

    legacy_dark_mode = cfg.pop("dark_mode", None)
    cfg.pop("theme_text", None)

    if not raw_theme:
        cfg["theme"] = "dark_theme" if legacy_dark_mode else "Light Theme"
    cfg["theme"] = normalize_theme(cfg["theme"])

    return cfg


def _read_config_file():
    path = get_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        print(f"No se pudo leer {path}: {e}")
        return {}


def _write_config(config):
    path = get_config_path()
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    os.replace(tmp_path, path)


def load_config():
    """
    Load the configuration, migrating/normalizing it on the fly.
    Returns a dict that always contains every DEFAULT_CONFIG key.
    """
    raw = _read_config_file()
    config = normalize_config(raw)
    if raw != config:
        try:
            _write_config(config)
        except OSError as e:
            print(f"No se pudo guardar la configuración normalizada: {e}")
    return config


def save_config(updated_data=None):
    """Merge ``updated_data`` into the existing config and persist it."""
    config = normalize_config(_read_config_file())
    if updated_data:
        config.update(updated_data)
    config = normalize_config(config)
    try:
        _write_config(config)
    except OSError as e:
        print(f"No se pudo guardar la configuración: {e}")
    return config


def get_theme_stylesheet(theme_name):
    """
    Return the QSS contents for ``theme_name``.
    Empty string means "Light Theme" (no stylesheet), None means the QSS
    file could not be found.
    """
    theme = normalize_theme(theme_name)
    if theme == "Light Theme":
        return ""

    qss_file = get_resource_path(os.path.join("themes", f"{theme}.qss"))
    try:
        with open(qss_file, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        print(f"Tema {theme} no encontrado en {qss_file}")
        return None


def make_relative_path(absolute_path):
    """
    Converts an absolute path to a relative path if the file is inside
    the program's base directory. Otherwise returns the absolute path unchanged.
    This ensures icon paths stored in the DB are portable when moving the app folder.
    """
    base_path = get_app_dir()

    try:
        relative = os.path.relpath(absolute_path, base_path)
        # If the relative path goes outside the base dir (starts with '..'), keep absolute
        if not relative.startswith('..'):
            # Normalize to forward slashes for consistency
            return relative.replace('\\', '/')
    except ValueError:
        # On Windows, relpath raises ValueError for paths on different drives
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
            subprocess.Popen(['osascript', '-e', f'tell application "Terminal" to do script "{command}"'])
            return True

        terminal_emulators = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xfce4-terminal', 'xterm']
        for term in terminal_emulators:
            term_path = shutil.which(term)
            if not term_path:
                continue
            try:
                if term == 'gnome-terminal':
                    subprocess.Popen([term_path, '--', 'bash', '-lc', command])
                else:
                    subprocess.Popen([term_path, '-e', 'bash', '-lc', command])
                return True
            except OSError as e:
                print(f"No se pudo abrir {term}: {e}")
                continue

        print("No se encontró un emulador de terminal disponible (xterm, gnome-terminal, konsole...).")
        return False
    except Exception as e:
        print(f"Error opening terminal: {e}")
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


def clean_text_format(editor, on_after_clean=None):
    """
    Remove rich text formatting (background colors, fonts)
    and leave only plain text.
    """
    cursor = editor.textCursor()
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.Document)

    if cursor.hasSelection():
        text_puro = cursor.selectedText().replace('\u2029', '\n')

        clean_char_fmt = QTextCharFormat()
        clean_block_fmt = QTextBlockFormat()

        cursor.setBlockFormat(clean_block_fmt)
        cursor.setCharFormat(clean_char_fmt)
        cursor.insertText(text_puro, clean_char_fmt)

        editor.setFocus()

        if on_after_clean:
            on_after_clean()

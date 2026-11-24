import sys, os, subprocess, webbrowser
from PySide6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat 

def is_windows():
    return sys.platform.startswith('win')

def is_macos():
    return sys.platform == 'darwin'

def is_linux():
    return sys.platform.startswith('linux')

def get_data_dir(folder_name):
    """
    Returns the persistent directory path for user data (e.g. 'mongita_data', 'storage').
    When frozen (PyInstaller executable):
      1. If the executable is in a folder containing '_internal/<folder_name>', use that.
      2. If '<folder_name>' exists next to the executable, use that.
      3. If '_internal' folder exists next to the executable and is writable, use '_internal/<folder_name>'.
      4. If the directory containing the executable is writable, put it next to the executable.
      5. Fallback for read-only locations (e.g. /usr/bin/): use ~/.myapp/<folder_name>.
    When not frozen (development):
      Uses './<folder_name>' relative to project root.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))

        # Check existing data in _internal/ (Windows onedir or folder with _internal)
        internal_data = os.path.join(exe_dir, "_internal", folder_name)
        if os.path.exists(internal_data):
            return internal_data

        # Check existing data directly next to the executable
        direct_data = os.path.join(exe_dir, folder_name)
        if os.path.exists(direct_data):
            return direct_data

        # If _internal exists and is writable, place data inside _internal
        internal_dir = os.path.join(exe_dir, "_internal")
        if os.path.isdir(internal_dir) and os.access(internal_dir, os.W_OK):
            target = os.path.join(internal_dir, folder_name)
            os.makedirs(target, exist_ok=True)
            return target

        # If executable directory is writable, place data next to executable
        if os.access(exe_dir, os.W_OK):
            target = os.path.join(exe_dir, folder_name)
            os.makedirs(target, exist_ok=True)
            return target

        # Fallback to user home config folder
        user_data_dir = os.path.join(os.path.expanduser("~"), ".myapp", folder_name)
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        target = os.path.join(base_path, folder_name)
        os.makedirs(target, exist_ok=True)
        return target

def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller
    """
    if not relative_path:
        return ""

    # Normalize Windows backslashes
    norm_path = relative_path.replace("\\", "/")

    # If the path is a full Windows/Linux path containing 'assets/', extract the relative 'assets/...' part
    if "assets/" in norm_path:
        relative_path = "assets/" + norm_path.split("assets/", 1)[1]

    if getattr(sys, 'frozen', False):
        # 1. First check inside PyInstaller temporary directory (sys._MEIPASS)
        meipass_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_path):
            return meipass_path

        # 2. Check next to executable or inside _internal/
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        direct_path = os.path.join(exe_dir, relative_path)
        if os.path.exists(direct_path):
            return direct_path

        internal_path = os.path.join(exe_dir, "_internal", relative_path)
        if os.path.exists(internal_path):
            return internal_path

        # 3. If still not found, check if it exists directly on this machine
        if os.path.exists(relative_path):
            return relative_path

        return meipass_path
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        cand = os.path.join(base_path, relative_path)
        if os.path.exists(cand):
            return cand
        if os.path.exists(relative_path):
            return relative_path
        return cand

def make_relative_path(absolute_path):
    """
    Converts an absolute path to a relative path if the file is inside
    the program's base directory. Otherwise returns the absolute path unchanged.
    This ensures icon paths stored in the DB are portable when moving the app folder.
    """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_path = os.path.abspath(".")
    
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
    """
    try:
        if is_windows():
            subprocess.Popen(f'start cmd /k "{command}"', shell=True)
        elif is_macos():
            subprocess.Popen(['osascript', '-e', f'tell application "Terminal" to do script "{command}"'])
        else:
            terminal_emulators = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xterm']
            for term in terminal_emulators:
                try:
                    subprocess.Popen([term, '-e', command])
                    break
                except FileNotFoundError:
                    continue
    except Exception as e:
        print(f"Error opening terminal: {e}")

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
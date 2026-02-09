import  sys, os, subprocess
from PySide6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat 

def is_windows():
    return sys.platform.startswith('win')

def is_macos():
    return sys.platform == 'darwin'

def is_linux():
    return sys.platform.startswith('linux')

def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
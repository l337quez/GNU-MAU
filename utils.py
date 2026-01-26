import  sys, os
from PySide6.QtGui import QTextCursor, QTextCharFormat 

def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)



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
        
        clean_format = QTextCharFormat() 
        cursor.setCharFormat(clean_format)
        cursor.insertText(text_puro)
        
        editor.setFocus()
        
        if on_after_clean:
            on_after_clean()
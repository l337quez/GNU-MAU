from PySide6.QtWidgets import QTextEdit, QApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt
import sys

class TodoTextEditor(QTextEdit): 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.WidgetWidth) 
        self.setPlaceholderText("Escribe tus tareas y pendientes aquí...")
        self.setUndoRedoEnabled(True)
        self.setMouseTracking(True)
        #self.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 16px; line-height: 1.4;")

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.position().toPoint())
        block = cursor.block()
        txt = block.text().lstrip()
        
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        char = cursor.selectedText()
        
        if char in ["☐", "☑"] or (txt.startswith(("☐", "☑")) and cursor.positionInBlock() <= 3):
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
        
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.position().toPoint())
            block = cursor.block()
            block_text = block.text()
            
            # Caso 1: Clic cerca del inicio de línea donde hay un checkbox
            lstripped = block_text.lstrip()
            if lstripped.startswith(("☐", "☑")) and cursor.positionInBlock() <= 4:
                char_idx = block_text.find("☐") if "☐" in block_text else block_text.find("☑")
                if char_idx != -1:
                    edit_cursor = QTextCursor(block)
                    edit_cursor.setPosition(block.position() + char_idx)
                    edit_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    curr = edit_cursor.selectedText()
                    new_char = "☑" if curr == "☐" else "☐"
                    edit_cursor.insertText(new_char)
                    self.viewport().update()
                    self.textChanged.emit()
                    return

            # Caso 2: Clic directo sobre el carácter checkbox
            check_cursor = QTextCursor(cursor)
            check_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            char_right = check_cursor.selectedText()

            check_cursor.setPosition(cursor.position())
            check_cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
            char_left = check_cursor.selectedText()

            target_char = ""
            direction = None

            if char_right in ["☐", "☑"]:
                target_char = char_right
                direction = "right"
            elif char_left in ["☐", "☑"]:
                target_char = char_left
                direction = "left"

            if target_char:
                new_char = "☑" if target_char == "☐" else "☐"
                edit_cursor = QTextCursor(cursor)
                if direction == "left":
                    edit_cursor.movePosition(QTextCursor.Left)
                edit_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                edit_cursor.insertText(new_char)
                self.viewport().update()
                self.textChanged.emit()
                return

        super().mousePressEvent(event)

    def add_checkboxes_to_selected_text(self):
        cursor = self.textCursor()
        self.document().beginUndoBlock()
        
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText("☐ ")
        else:
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start)
            
            while cursor.position() < end:
                cursor.movePosition(QTextCursor.StartOfBlock)
                txt = cursor.block().text()
                # Evitamos poner doble checkbox
                if not (txt.strip().startswith("☐") or txt.strip().startswith("☑")):
                    cursor.insertText("☐ ")
                    end += 2
                if not cursor.movePosition(QTextCursor.NextBlock):
                    break
                    
        self.document().endUndoBlock()
        self.textChanged.emit()

if __name__ == '__main__':
    app = QApplication([])
    editor = TodoTextEditor()
    editor.setPlainText(" ☐ Task indented (now working)\n☑ Task completed")
    editor.resize(400, 300)
    editor.show()
    sys.exit(app.exec())
from PySide6.QtWidgets import QTextEdit, QApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt
import sys

class TodoTextEditor(QTextEdit): 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.WidgetWidth) 
        self.setPlaceholderText("Write your notes and assignments here...")
        self.setUndoRedoEnabled(True) 
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        cursor = self.cursorForPosition(pos)
        if cursor.positionInBlock() <= 3:
            text = cursor.block().text()
            if "☐" in text[:5] or "☑" in text[:5]:
                self.viewport().setCursor(Qt.ArrowCursor)
                return
        self.viewport().setCursor(Qt.IBeamCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Usar el cursor de la posición del click
            click_pos = self.cursorForPosition(event.position().toPoint())
            block = click_pos.block()
            line_text = block.text()
            
            # Solo actuar si el clic es al inicio (zona del checkbox)
            if click_pos.positionInBlock() <= 3:
                has_box = "☐" in line_text[:5]
                has_check = "☑" in line_text[:5]

                if has_box or has_check:
                    # 1. Crear un cursor específico para la edición
                    edit_cursor = QTextCursor(block)
                    
                    # 2. Buscar el índice real del símbolo
                    idx = line_text.find("☐") if has_box else line_text.find("☑")
                    char_to_insert = "☑" if has_box else "☐"

                    if idx != -1:
                        # 3. Posicionar y seleccionar el carácter
                        edit_cursor.setPosition(block.position() + idx)
                        edit_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
                        
                        # 4. Insertar texto a través del documento para asegurar que se emita textChanged
                        self.document().beginUndoBlock()
                        edit_cursor.insertText(char_to_insert)
                        self.document().endUndoBlock()
                        
                        # 5. ACTUALIZACIÓN CRÍTICA:
                        # Establecemos el cursor del widget en la misma posición para que el editor
                        # reconozca el foco y el cambio de contenido.
                        self.setTextCursor(edit_cursor)
                        
                        # Forzar el refresco de la interfaz
                        self.viewport().update()
                        
                        # Emitir manualmente por si acaso, aunque insertText ya debería hacerlo
                        self.textChanged.emit() 
                        
                        event.accept()
                        return

        # Si no fue clic en checkbox, procesar normal
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
                if not (txt.startswith("☐") or txt.startswith("☑")):
                    cursor.insertText("☐ ")
                    # Ajustar el final de la selección por el nuevo texto
                    end += 2
                if not cursor.movePosition(QTextCursor.NextBlock):
                    break
                    
        self.document().endUndoBlock()
        self.textChanged.emit()

if __name__ == '__main__':
    app = QApplication([])
    editor = TodoTextEditor()
    editor.setPlainText("☐ Tarea 1\n☑ Tarea 2")
    editor.setWindowTitle("Todo Editor")
    editor.resize(400, 300)
    editor.show()
    sys.exit(app.exec())
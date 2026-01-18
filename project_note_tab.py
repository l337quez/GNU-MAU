from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton,
                               QHBoxLayout, QLineEdit, QListWidget, 
                               QListWidgetItem, QMessageBox, QSplitter, 
                               QInputDialog, QStackedWidget)
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtCore import Slot, Qt
import os
import markdown2


from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt

from emoji_picker import  EmojiPicker

class ProjectNoteTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("ProjectNoteTab")
        self.current_note_file = None
        self.project_id = None
        self.notes_dir = ""

        # --- NUEVO: CSS MEJORADO PARA TABLAS ---
        self.preview_css = """
        <style>
            body { font-family: 'Segoe UI', sans-serif; padding: 20px; line-height: 1.6; color: #333; }
            h1, h2, h3 { color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px; }
            
            /* Estilos para código */
            pre { background-color: #f4f4f4; border: 1px solid #ddd; padding: 10px; border-radius: 5px; font-family: 'Consolas', monospace; }
            code { background-color: #f4f4f4; color: #c7254e; padding: 2px 4px; border-radius: 3px; font-family: 'Consolas', monospace; }
            
            /* Estilo para Citas */
            blockquote { border-left: 5px solid #3498db; margin: 10px 0; padding: 10px 20px; color: #555; background-color: #f0f8ff; }
            
            /* NUEVO: Estilos para Tablas */
            table { border-collapse: collapse; width: 100%; margin: 15px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; color: #333; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            
            /* Estilo para Links */
            a { color: #3498db; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
        </style>
        """

        self.main_layout = QVBoxLayout(self)

        # --- EXPLORADOR ---
        self.explorer_group = QWidget()
        self.explorer_layout = QVBoxLayout(self.explorer_group)
        self.top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search note...")
        self.search_input.setFixedHeight(28)
        self.new_note_btn = QPushButton("📄 New") # Texto más corto
        self.new_note_btn.setFixedHeight(28)
        self.top_bar.addWidget(self.search_input)
        self.top_bar.addWidget(self.new_note_btn)
        self.explorer_layout.addLayout(self.top_bar)
        
        self.notes_list_widget = QListWidget()
        self.notes_list_widget.itemClicked.connect(self.open_selected_note)
        self.explorer_layout.addWidget(self.notes_list_widget)

        # --- EDITOR ---
        self.editor_group = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_group)

        # Toolbar
        self.toolbar = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_current_note)
        
        self.mode_btn = QPushButton("✏️ Edit")
        self.mode_btn.setCheckable(True)
        self.mode_btn.setChecked(True) 
        self.mode_btn.toggled.connect(self.toggle_mode)

        self.toolbar.addWidget(self.save_btn)
        self.toolbar.addWidget(self.mode_btn)
        
        # --- NUEVOS BOTONES DE FORMATO ---
        self.toolbar.addSpacing(15)
        
        self.emoji_btn = QPushButton("😊")
        self.bold_btn = QPushButton("B")
        self.italic_btn = QPushButton("I")
        self.header_btn = QPushButton("H1")     
        self.list_btn = QPushButton("List")     
        self.link_btn = QPushButton("🔗")      
        self.quote_btn = QPushButton("❞")
        self.code_btn = QPushButton("<>")
        
        # Lista de todos los botones de formato para controlarlos fácil
        self.format_btns = [
            self.emoji_btn, self.bold_btn, self.italic_btn, self.header_btn, 
            self.list_btn, self.link_btn, self.quote_btn, self.code_btn,
            self.code_btn
        ]

        for btn in self.format_btns: 
            btn.setFixedWidth(35) # Un poco más anchos para que quepan iconos
            if btn == self.list_btn: btn.setFixedWidth(40)
            btn.setEnabled(False) 

        # Agregar botones al layout
        self.toolbar.addWidget(self.emoji_btn)
        self.toolbar.addWidget(self.header_btn)
        self.toolbar.addWidget(self.bold_btn)
        self.toolbar.addWidget(self.italic_btn)
        self.toolbar.addWidget(self.list_btn)
        self.toolbar.addWidget(self.link_btn)
        self.toolbar.addWidget(self.quote_btn)
        self.toolbar.addWidget(self.code_btn)
        
        self.toolbar.addStretch()
        self.editor_layout.addLayout(self.toolbar)

        # Stacked Widget
        self.stack = QStackedWidget()
        self.edit_area = QTextEdit()
        self.edit_area.setPlaceholderText("Write your notes here... Use Markdown!")
        self.edit_area.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 15px;")
        
        self.view_area = QTextEdit()
        self.view_area.setReadOnly(True)
        
        self.stack.addWidget(self.edit_area) 
        self.stack.addWidget(self.view_area) 
        self.editor_layout.addWidget(self.stack)

        # Splitter
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.explorer_group)
        self.splitter.addWidget(self.editor_group)
        self.splitter.setSizes([150, 400])
        self.main_layout.addWidget(self.splitter)
        
        # Conexiones
        self.new_note_btn.clicked.connect(self.create_new_note)
        self.search_input.textChanged.connect(self.filter_notes)
        
        # Lógica de inserción
        self.bold_btn.clicked.connect(lambda: self.insert_md("**", "**"))
        self.italic_btn.clicked.connect(lambda: self.insert_md("*", "*"))
        self.quote_btn.clicked.connect(lambda: self.insert_md("> ", ""))
        self.code_btn.clicked.connect(lambda: self.insert_md("```\n", "\n```"))
        
        # --- NUEVAS CONEXIONES ---
        self.header_btn.clicked.connect(lambda: self.insert_md("# ", ""))
        self.list_btn.clicked.connect(lambda: self.insert_md("- ", ""))
        self.link_btn.clicked.connect(lambda: self.insert_md("[", "](url)")) # Inserta formato link

        # Conectamos el botón a la nueva función
        self.emoji_btn.clicked.connect(self.open_emoji_picker)
        self.setEnabled(False)

    # ... (set_project_id y load_notes_from_dir son iguales) ...
    def set_project_id(self, project_id):
        self.project_id = str(project_id)
        self.notes_list_widget.clear()
        self.edit_area.clear()
        self.view_area.clear()
        self.current_note_file = None
        if project_id:
            self.setEnabled(True)
            self.notes_dir = os.path.join(self.main_window.storage_dir, self.project_id)
            if not os.path.exists(self.notes_dir):
                try: os.makedirs(self.notes_dir)
                except OSError: pass
            self.load_notes_from_dir()
        else:
            self.setEnabled(False)

    def load_notes_from_dir(self):
        self.notes_list_widget.clear()
        if os.path.exists(self.notes_dir):
            files = [f for f in os.listdir(self.notes_dir) if f.endswith(('.md', '.txt'))]
            for f in files:
                item = QListWidgetItem(f"📄 {f}")
                item.setData(Qt.UserRole, os.path.join(self.notes_dir, f))
                self.notes_list_widget.addItem(item)

    # --- FUNCIÓN AUXILIAR PARA RENDERIZAR MARKDOWN ---
    def render_markdown(self):
        raw_text = self.edit_area.toPlainText()
        # NUEVO: Agregamos "tables" a los extras
        html = markdown2.markdown(raw_text, extras=["fenced-code-blocks", "blockquote", "tables"])
        self.view_area.setHtml(self.preview_css + html)

    @Slot(bool)
    def toggle_mode(self, checked):
        if checked:
            self.mode_btn.setText("✏️ Edit")
            self.render_markdown() # Usamos la función auxiliar
            self.stack.setCurrentIndex(1)
            # Deshabilitar todos los botones de formato
            for btn in self.format_btns:
                btn.setEnabled(False)
        else:
            self.mode_btn.setText("👁️ Preview")
            self.stack.setCurrentIndex(0)
            # Habilitar todos los botones de formato
            for btn in self.format_btns:
                btn.setEnabled(True)
            self.edit_area.setFocus()

    @Slot()
    def open_selected_note(self, item):
        self.current_note_file = item.data(Qt.UserRole)
        if os.path.exists(self.current_note_file):
            try:
                with open(self.current_note_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.edit_area.setPlainText(content)
                    
                    self.render_markdown() # Renderizar
                    
                    self.mode_btn.setChecked(True)
                    self.stack.setCurrentIndex(1)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir la nota: {e}")

    @Slot()
    def save_current_note(self):
        if self.current_note_file:
            try:
                content = self.edit_area.toPlainText()
                with open(self.current_note_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                if self.mode_btn.isChecked():
                    self.render_markdown() # Renderizar
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save: {e}")

    # ... (insert_md, create_new_note y filter_notes son iguales) ...
    def insert_md(self, prefix, suffix):
        if self.stack.currentIndex() != 0: return 
        cursor = self.edit_area.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            cursor.insertText(f"{prefix}{suffix}")
            # Si hay sufijo (como en link), movemos el cursor al medio
            # Si no hay sufijo (como en lista), se queda al final
            if suffix: 
                cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
        self.edit_area.setFocus()

    @Slot()
    def create_new_note(self):
        name, ok = QInputDialog.getText(self, "New Nota", "File name:")
        if ok and name:
            if not name.endswith(".md"): name += ".md"
            path = os.path.join(self.notes_dir, name)
            try:
                with open(path, 'w', encoding='utf-8') as f: 
                    f.write(f"# {name[:-3]}\n\n Write here...")
                self.load_notes_from_dir()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def filter_notes(self, text):
        for i in range(self.notes_list_widget.count()):
            item = self.notes_list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def open_emoji_picker(self):
            # Solo funciona si estamos en modo edición
            if self.stack.currentIndex() != 0: return

            dialog = EmojiPicker(self)
            # .exec() detiene el programa hasta que se cierra la ventana
            if dialog.exec(): 
                if dialog.selected_emoji:
                    # Insertamos el emoji seleccionado
                    self.insert_md(dialog.selected_emoji, "")
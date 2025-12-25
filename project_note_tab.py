from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton,
                               QHBoxLayout, QLineEdit, QListWidget, 
                               QListWidgetItem, QMessageBox, QSplitter, 
                               QInputDialog, QStackedWidget)
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtCore import Slot, Qt
import os
import markdown2

class ProjectNoteTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("ProjectNoteTab")
        self.current_note_file = None
        self.project_id = None
        self.notes_dir = ""

        # Estilo para el modo Preview (Cajitas de código y citas)
        self.preview_css = """
        <style>
            body { font-family: 'Segoe UI', sans-serif; padding: 20px; line-height: 1.6; color: #333; }
            h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 5px; }
            pre { background-color: #f4f4f4; border: 1px solid #ddd; padding: 10px; border-radius: 5px; font-family: 'Consolas', monospace; }
            code { background-color: #f4f4f4; color: #c7254e; padding: 2px 4px; border-radius: 3px; font-family: 'Consolas', monospace; }
            blockquote { border-left: 5px solid #bdc3c7; margin: 10px 0; padding: 10px 20px; color: #7f8c8d; background-color: #f9f9f9; }
        </style>
        """

        self.main_layout = QVBoxLayout(self)

        # --- EXPLORADOR ---
        self.explorer_group = QWidget()
        self.explorer_layout = QVBoxLayout(self.explorer_group)
        self.top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search note...")
        self.new_note_btn = QPushButton("📄 New note")
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
        
        # Botón de modo: Inicia configurado para Preview
        self.mode_btn = QPushButton("✏️ Edit")
        self.mode_btn.setCheckable(True)
        self.mode_btn.setChecked(True) 
        self.mode_btn.toggled.connect(self.toggle_mode)

        self.toolbar.addWidget(self.save_btn)
        self.toolbar.addWidget(self.mode_btn)
        
        # Botones de formato
        self.bold_btn = QPushButton("B")
        self.italic_btn = QPushButton("I")
        self.quote_btn = QPushButton("❞")
        self.code_btn = QPushButton("<>")
        
        for btn in [self.bold_btn, self.italic_btn, self.quote_btn]: 
            btn.setFixedWidth(30)
            btn.setEnabled(False) # Inician deshabilitados porque empezamos en Preview
        self.code_btn.setFixedWidth(40)
        self.code_btn.setEnabled(False)

        self.toolbar.addSpacing(10)
        self.toolbar.addWidget(self.bold_btn)
        self.toolbar.addWidget(self.italic_btn)
        self.toolbar.addWidget(self.quote_btn)
        self.toolbar.addWidget(self.code_btn)
        self.toolbar.addStretch()
        self.editor_layout.addLayout(self.toolbar)

        # Stacked Widget
        self.stack = QStackedWidget()
        self.edit_area = QTextEdit()
        self.edit_area.setPlaceholderText("Write your notes here...")
        self.edit_area.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 15px;")
        
        self.view_area = QTextEdit()
        self.view_area.setReadOnly(True)
        
        self.stack.addWidget(self.edit_area) # Index 0
        self.stack.addWidget(self.view_area) # Index 1
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
        self.bold_btn.clicked.connect(lambda: self.insert_md("**", "**"))
        self.italic_btn.clicked.connect(lambda: self.insert_md("*", "*"))
        self.quote_btn.clicked.connect(lambda: self.insert_md("> ", ""))
        self.code_btn.clicked.connect(lambda: self.insert_md("```\n", "\n```"))

        self.setEnabled(False)


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

    @Slot(bool)
    def toggle_mode(self, checked):
        """
        If checked (True), we are in Preview mode. If False, Edit mode.
        """
        if checked:
            self.mode_btn.setText("✏️ Edit")
            raw_text = self.edit_area.toPlainText()
            html = markdown2.markdown(raw_text, extras=["fenced-code-blocks", "blockquote"])
            self.view_area.setHtml(self.preview_css + html)
            self.stack.setCurrentIndex(1)
            # Deshabilitar botones de formato
            for btn in [self.bold_btn, self.italic_btn, self.quote_btn, self.code_btn]:
                btn.setEnabled(False)
        else:
            self.mode_btn.setText("👁️ Preview")
            self.stack.setCurrentIndex(0)
            # Habilitar botones de formato
            for btn in [self.bold_btn, self.italic_btn, self.quote_btn, self.code_btn]:
                btn.setEnabled(True)

    @Slot()
    def open_selected_note(self, item):
        self.current_note_file = item.data(Qt.UserRole)
        if os.path.exists(self.current_note_file):
            try:
                with open(self.current_note_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Cargamos el texto en el editor de fondo
                    self.edit_area.setPlainText(content)
                    
                    # Forzamos el renderizado inmediato para el preview
                    html = markdown2.markdown(content, extras=["fenced-code-blocks", "blockquote"])
                    self.view_area.setHtml(self.preview_css + html)
                    
                    # Activamos el modo Preview visualmente
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
                # Si estamos en modo preview, refrescar la vista al guardar
                if self.mode_btn.isChecked():
                    html = markdown2.markdown(content, extras=["fenced-code-blocks", "blockquote"])
                    self.view_area.setHtml(self.preview_css + html)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save: {e}")

    def insert_md(self, prefix, suffix):
        if self.stack.currentIndex() != 0: return 
        cursor = self.edit_area.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            cursor.insertText(f"{prefix}{suffix}")
            if suffix: cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
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
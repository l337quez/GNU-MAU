"""
GNU Mau - Internationalization (i18n) module.
Provides translations for English (default) and Spanish.
"""

import os
import json

CURRENT_LANGUAGE = "en"

TRANSLATIONS = {
    "en": {
        # App & Window
        "app_title": "GNU Mau",
        "projects_dock": "Projects",
        "create_project": "➕ Create Project",
        "tools_btn": "🚀 Tools",
        "settings_tooltip": "Settings",
        "about_tooltip": "About",
        "tray_show": "Show",
        "tray_quit": "Quit",
        "back_to_projects": "⬅ Back to Projects",
        "collapse_sidebar": "Collapse sidebar",
        "expand_sidebar": "Expand sidebar",
        
        # Tabs
        "tab_project": "Project",
        "tab_information": "Information",
        "tab_todo": "Todo",
        "tab_note": "Note",
        "tab_diagram": "Diagram",
        
        # Project Tab
        "project_name": "Project name",
        "project_description": "Project description",
        "key_placeholder": "Key...",
        "value_placeholder": "Value...",
        "category_placeholder": "Category",
        "action_none": "🚫 None",
        "action_terminal": "💻 Terminal",
        "action_browser": "🌐 Browser",
        "table_key": "Key",
        "table_value": "Value",
        "table_actions": "Actions",
        "btn_save": "💾 Save",
        "btn_gif": "🖼️ Gif",
        
        # Todo Tab
        "view_list": "📋 List View",
        "view_board": "📊 Board View",
        "search_tasks_placeholder": "🔍 Search tasks...",
        "add_column": "➕ Add Column",
        "add_column_prompt": "Column name:",
        "rename_column": "Rename Column",
        "delete_column": "Delete Column",
        "card_moved": "Moved to",
        "card_detail_title": "Edit Task",
        "column_label": "Column:",
        "new_list": "➕ New List",
        "refresh": "🔄 Refresh",
        "delete_list": "🗑️ Delete List",
        "insert_task": "☐ Insert task",
        "clean_format": "Clean format",
        "bold": "Bold",
        "copy_tasks": "Copy tasks",
        "list_title_placeholder": "List title...",
        "no_tasks_placeholder": "No tasks in this project. Click '➕ New List' to create one.",
        "status_saved": "✓ Saved",
        "status_saving": "⏳ Saving...",
        "copied_to_clipboard": "✓ Copied to clipboard!",
        "nothing_to_copy": "Nothing to copy.",
        "delete_todo_confirm": "Delete this TODO list?",
        "btn_yes_delete": "Yes, Delete",
        "btn_cancel": "Cancel",
        "default_new_todo_title": "New List",
        "default_new_task": "☐ My first task",
        
        # Notes Tab
        "search_note": "🔍 Search note...",
        "new_note": "📄 New note",
        "delete_note_confirm": "Delete note?",
        "write_notes_placeholder": "Write your notes here... Use Markdown or formatting buttons!",
        
        # Settings Tab
        "settings_title": "Settings",
        "theme_label": "Theme:",
        "language_label": "Language:",
        "sidebar_position": "Sidebar position",
        "pos_left": "Left",
        "pos_right": "Right",
        "pos_top": "Top",
        "pos_bottom": "Bottom",
        "minimize_to_tray": "Minimize to tray when closing",
        "allow_ai": "Allow AI to create and manage tasks (AI Integration)",
        "allow_ai_tooltip": "Enables external AI assistants to manage tasks and notes in GNU Mau.",
        "check_updates": "Check for updates",
        "lang_restart_notice": "Language updated successfully.",
        
        # About Tab
        "about_title": "About GNU Mau",
        "about_subtitle": "Modular Application Utility",
    },
    "es": {
        # App & Window
        "app_title": "GNU Mau",
        "projects_dock": "Proyectos",
        "create_project": "➕ Crear Proyecto",
        "tools_btn": "🚀 Herramientas",
        "settings_tooltip": "Configuración",
        "about_tooltip": "Acerca de",
        "tray_show": "Mostrar",
        "tray_quit": "Salir",
        "back_to_projects": "⬅ Volver a Proyectos",
        "collapse_sidebar": "Colapsar barra lateral",
        "expand_sidebar": "Expandir barra lateral",
        
        # Tabs
        "tab_project": "Proyecto",
        "tab_information": "Información",
        "tab_todo": "Tareas",
        "tab_note": "Notas",
        "tab_diagram": "Diagramas",
        
        # Project Tab
        "project_name": "Nombre del proyecto",
        "project_description": "Descripción del proyecto",
        "key_placeholder": "Clave...",
        "value_placeholder": "Valor...",
        "category_placeholder": "Categoría",
        "action_none": "🚫 Ninguna",
        "action_terminal": "💻 Terminal",
        "action_browser": "🌐 Navegador",
        "table_key": "Clave",
        "table_value": "Valor",
        "table_actions": "Acciones",
        "btn_save": "💾 Guardar",
        "btn_gif": "🖼️ Gif",
        
        # Todo Tab
        "view_list": "📋 Vista Lista",
        "view_board": "📊 Vista Tablero",
        "search_tasks_placeholder": "🔍 Buscar tareas...",
        "add_column": "➕ Nueva Columna",
        "add_column_prompt": "Nombre de la columna:",
        "rename_column": "Renombrar Columna",
        "delete_column": "Eliminar Columna",
        "card_moved": "Movido a",
        "card_detail_title": "Editar Tarea",
        "column_label": "Columna:",
        "new_list": "➕ Nueva lista",
        "refresh": "🔄 Actualizar",
        "delete_list": "🗑️ Eliminar lista",
        "insert_task": "☐ Insertar tarea",
        "clean_format": "Limpiar formato",
        "bold": "Negrita",
        "copy_tasks": "Copiar tareas",
        "list_title_placeholder": "Título de la lista...",
        "no_tasks_placeholder": "No hay tareas en este proyecto. Haz clic en '➕ Nueva lista'.",
        "status_saved": "✓ Guardado",
        "status_saving": "⏳ Guardando...",
        "copied_to_clipboard": "✓ ¡Copiado al portapapeles!",
        "nothing_to_copy": "Nada que copiar.",
        "delete_todo_confirm": "¿Eliminar esta lista de tareas?",
        "btn_yes_delete": "Sí, Eliminar",
        "btn_cancel": "Cancelar",
        "default_new_todo_title": "Nueva lista",
        "default_new_task": "☐ Mi primera tarea",
        
        # Notes Tab
        "search_note": "🔍 Buscar nota...",
        "new_note": "📄 Nueva nota",
        "delete_note_confirm": "¿Eliminar nota?",
        "write_notes_placeholder": "Escribe tus notas aquí... ¡Usa Markdown o los botones de formato!",
        
        # Settings Tab
        "settings_title": "Configuración",
        "theme_label": "Tema:",
        "language_label": "Idioma:",
        "sidebar_position": "Posición de barra lateral",
        "pos_left": "Izquierda",
        "pos_right": "Derecha",
        "pos_top": "Arriba",
        "pos_bottom": "Abajo",
        "minimize_to_tray": "Minimizar a la bandeja al cerrar",
        "allow_ai": "Permitir que la IA cree y gestione tareas (Integración IA)",
        "allow_ai_tooltip": "Permite a asistentes de IA gestionar tareas y notas en GNU Mau.",
        "check_updates": "Buscar actualizaciones",
        "lang_restart_notice": "Idioma actualizado correctamente.",
        
        # About Tab
        "about_title": "Acerca de GNU Mau",
        "about_subtitle": "Modular Application Utility",
    }
}


def get_language() -> str:
    """Returns the current language code ('en' or 'es')."""
    return CURRENT_LANGUAGE


def set_language(lang_code: str):
    """Sets the active language code."""
    global CURRENT_LANGUAGE
    if lang_code in TRANSLATIONS:
        CURRENT_LANGUAGE = lang_code
    else:
        CURRENT_LANGUAGE = "en"


def tr(key: str, default: str = None) -> str:
    """
    Translates a key into the currently active language.
    Falls back to English, then to default, then to key itself.
    """
    lang_dict = TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS["en"])
    if key in lang_dict:
        return lang_dict[key]
    en_dict = TRANSLATIONS.get("en", {})
    if key in en_dict:
        return en_dict[key]
    return default if default is not None else key


def get_supported_languages() -> dict:
    """Returns supported language codes mapped to their display names."""
    return {
        "en": "English",
        "es": "Español"
    }

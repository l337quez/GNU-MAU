<p align="center">
  <img src="assets/app/mau.png" alt="GNU Mau Logo" width="400">
</p>

# GNU Mau 😸🔧

**GNU Mau** (Multipurpose Automation Utility) is a specialized productivity tool designed for **Backend Engineers and DevOps Professionals**. It provides a centralized hub to organize projects, store critical commands, manage credentials, and keep track of daily tasks through a streamlined, themeable interface.

---

## ✨ Key Features

### � Project Management

- **Centralized Info**: Store project-specific credentials, URLs, and documentation.
- **Embedded Terminal**: Execute project commands directly from the interface using quick-access terminal buttons.
- **Quick Copy**: One-click copying for sensitive data like API keys or server IPs.

### ✅ Advanced TODO Lists

- **Rich Text Support**: Bold formatting for important tasks.
- **Emoji Picker**: Personalize your lists with a built-in emoji selector.
- **Auto-Save**: Never lose progress with background saving.
- **Quick Copy**: Share your task lists instantly with the "Copy to Clipboard" feature.

### 📝 Markdown Notes

- **Live Preview**: Write in Markdown and see the rendered result instantly.
- **Theme-Aware**: Preview styles adjust automatically to your active theme (Dark/Light/Arctic).
- **Clean Formatting**: Use the "Sweep" tool to strip formatting and keep your notes tidy.
- **Emoji & Links**: Full support for emojis and clickable hyperlink insertion.

### 📊 Interactive Diagrams

- **Node-Based Editor**: Create architecture diagrams, database schemas, or flowcharts using an intuitive drag-and-drop interface.
- **Powered by `qtpynodeeditor`**: Built on a robust, native framework for offline node-graph editing in Python.
- **Customizable Components**: Add specialized nodes for text, database tables with column listings, and more.
- **Project-Linked**: Diagrams are automatically organized and saved as JSON within each project's storage.

### 🎨 Premium UI & Customization

- **Dynamic Themes**: Choose from **Arctic Mist**, **Amber Dusk**, **Dark**, or **Light** themes.
- **System Tray**: Keep Mau running in the background for quick access.
- **Responsive Design**: Elegant layouts built with PySide6 for a native desktop feel.

---

## 🚀 Setup & Installation

Mau uses **Poetry** for robust dependency management, ensuring a consistent environment.

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)

### Getting Started

1. **Install Dependencies**:

   ```bash
   poetry install
   ```

2. **Activate Environment**:

   ```bash
   poetry shell
   ```

3. **Launch Application**:
   ```bash
   python main.py
   ```

_Tip: You can also run it directly using `poetry run python main.py`._

---

## 🛠️ Internal Development

To maintain a healthy codebase, please use Poetry for dependency changes:

- **Add Package**: `poetry add <package-name>`
- **Remove Package**: `poetry remove <package-name>`
- **Update Dependencies**: `poetry update`

---

## ⚙️ Configuration & Restoration

GNU Mau includes utilities for database management and restoration in the **Settings** tab. Always ensure you have a backup of your `projects_db` if performing manual restorations.

---

_Designed with 🐾 for efficiency._

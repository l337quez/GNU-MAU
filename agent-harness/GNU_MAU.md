# GNU Mau — CLI-Anything Analysis & SOP

## Software Overview
GNU Mau (Multipurpose Automation Utility) is a PySide6 desktop application for
backend engineers and DevOps professionals. It provides project management,
credential storage, TODO lists, Markdown notes, interactive node-based diagrams,
and developer tools (cURL client, port scanner, JWT decoder, IP calculator) —
all backed by a Mongita (local MongoDB-compatible) database.

## Backend Engine
- **Database**: Mongita (`MongitaClientDisk`) stored in `./mongita_data/`
- **File Storage**: Notes and diagrams stored in `./storage/<project_id>/`
- **Config**: JSON file at `~/.myapp/config.json`
- **GUI Framework**: PySide6 (Qt for Python)

## GUI → API Mapping

### Projects
| GUI Action               | Backend Call                                     |
|--------------------------|--------------------------------------------------|
| Create project           | `db.projects.insert_one({name, description, …})` |
| Select project           | `db.projects.find_one({_id: ObjectId(...)})` |
| Update project metadata  | `db.projects.update_one(...)` |
| Delete project           | *(not in GUI yet, but trivial via db)* |
| List projects            | `db.projects.find()` |
| Change icon              | `db.projects.update_one({icon_path: ...})` |

### Project Info (key-value store per project)
| GUI Action               | Backend Call                                     |
|--------------------------|--------------------------------------------------|
| Add info item            | Update `project.info` dict, then `update_one()`  |
| Edit info item           | Pop old key, insert new key/value in dict         |
| Delete info item         | `del current_project_info[key]`, then `update_one()` |
| Search/filter info       | In-memory filter by key name and category         |

### Todos
| GUI Action               | Backend Call                                     |
|--------------------------|--------------------------------------------------|
| Create TODO              | `db.todos.insert_one({title, content, project_id})` |
| Select TODO              | `db.todos.find_one({_id: ObjectId(...)})` |
| Update TODO              | `db.todos.update_one({$set: {title, content}})` |
| Delete TODO              | `db.todos.delete_one({_id: ObjectId(...)})` |
| List TODOs for project   | `db.todos.find({project_id: ...})` |

### Notes (file-based)
| GUI Action               | Backend Call                              |
|--------------------------|-------------------------------------------|
| Create note (.md/.txt)   | `open(path, 'w')` with initial content     |
| Open/read note           | `open(path, 'r').read()`                   |
| Save note                | `open(path, 'w').write(content)`            |
| Delete note              | `os.remove(path)`                           |
| List notes               | `os.listdir(notes_dir)` filtered by ext     |
| Rename note              | `os.rename(old_path, new_path)`             |

### Diagrams (qtpynodeeditor, file-based JSON)
| GUI Action                | Backend Call                              |
|---------------------------|-------------------------------------------|
| Create diagram            | New FlowScene, save as JSON                |
| Open/Load diagram         | FlowScene.__setstate__(json.load(f))       |
| Save diagram              | json.dump(FlowScene.__getstate__(), f)     |
| Delete diagram            | `os.remove(path)`                           |
| List diagrams             | `os.listdir(diagrams_dir)` filtered by .json |
| Add node (Text/DB/Diamond/etc) | `scene.create_node(model)` |
| Export as PNG              | `scene.render()` → QPixmap → save          |

### Tools
| Tool                     | Backend                                  |
|--------------------------|------------------------------------------|
| cURL client              | `subprocess.Popen(["curl", ...])` |
| Ping                     | `subprocess.Popen(["ping", ...])` |
| Port scanner             | `socket.connect_ex((host, port))`  |
| IP Calculator            | `ipaddress.ip_network(cidr)` |
| JWT Decoder              | `base64.urlsafe_b64decode(payload)` |
| Password Hasher          | `hashlib.pbkdf2_hmac(...)` |

### Settings
| GUI Action               | Backend Call                              |
|--------------------------|-------------------------------------------|
| Change theme             | Load QSS from `themes/` dir               |
| Sidebar position         | `addDockWidget(area, dock)`                |
| Minimize to tray toggle  | Save to `~/.myapp/config.json`             |
| Check for updates        | HTTP fetch from GitHub `version.txt`       |
| Restore from folder      | Batch file copy of `storage/` + `mongita_data/` |

## Data Model
- **projects** collection: `{_id, name, description, info: {}, icon_path}`
- **todos** collection: `{_id, title, content, project_id}`
- **categories** collection: *(planned, not fully used yet)*
- **Notes**: `./storage/<project_id>/*.md` or `*.txt` files
- **Diagrams**: `./storage/<project_id>/*.json` files
- **Config**: `~/.myapp/config.json`

## CLI Design Decisions
Since Mau uses Mongita (a local file-based MongoDB interface), the CLI can
directly instantiate `MongitaClientDisk` and perform all CRUD operations without
needing the PySide6 GUI running. Notes and diagrams are plain files on disk.
This makes our CLI a true direct-access interface, not a GUI-automation wrapper.

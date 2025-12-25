<p align="center">
  <img src="assets/app/mau.png" alt="GNU Mau Logo" width="400">
</p>

# GNU  Mau 😸​​🔧​
It is tool designed to organize and store commands, credentials, and project-specific information. Although it is primarily aimed at backend and DevOps programmers, anyone who finds it useful can take advantage of it.


 MAU  (Multipurpose Automation Utility)

</br>

## 🚀 Setup & Installation
This project uses Poetry for dependency management and virtual environment isolation, similar to how npm works for Node.js. This ensures that PySide6, gkeepapi, and other tools run in a consistent environment.

**Prerequisites**
Python 3.10+

Poetry: If you don't have it installed, run:

```bash
pip install poetry
```

Getting Started (New Environment)
If you have just cloned the repository or are setting it up on a new machine, follow these steps:

Install Dependencies: Run the following command in the project root. Poetry will read the pyproject.toml file, create a dedicated virtual environment, and install all required packages:

```bash
poetry install
```
Activate the Virtual Environment: To enter the project's isolated environment, run:


```bash
poetry shell
```
Run the Application: Once the environment is active, launch MAU:


```bash
python main.py
```

Alternatively, you can run it without entering the shell using: poetry run python main.py  

</br>

## 🛠️ Dependency Management
To keep the project healthy, avoid using pip directly. Instead, use Poetry commands:

```bash
Add a new package: poetry add <package-name>

Remove a package: poetry remove <package-name>

Update all packages: poetry update
```


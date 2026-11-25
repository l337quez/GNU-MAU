# CLI-Anything GNU Mau

CLI harness for **GNU Mau** (Multipurpose Automation Utility) — a PySide6/Mongita
productivity tool for backend engineers and DevOps professionals.

## Prerequisites

- Python 3.10+
- The GNU Mau source repository (this directory lives inside it)

## Installation

```bash
cd agent-harness
pip install -e .
```

## Usage

```bash
# Enter the interactive REPL
cli-anything-gnu-mau

# List all projects (human-readable)
cli-anything-gnu-mau project list

# List all projects (JSON for agents)
cli-anything-gnu-mau --json project list

# Create a new project
cli-anything-gnu-mau project new -n "My Infra" -d "Production servers"

# Add a key-value entry (credentials, URLs, etc.)
cli-anything-gnu-mau kv add -k "API_KEY" -v "sk-abc123" -a none -c "secrets"

# Create and manage TODOs
cli-anything-gnu-mau todo new -t "Setup CI/CD"
cli-anything-gnu-mau todo list

# Work with notes
cli-anything-gnu-mau note new -n "deploy-guide"
cli-anything-gnu-mau note show deploy-guide.md

# Create diagrams programmatically
cli-anything-gnu-mau diagram new -n "architecture"
cli-anything-gnu-mau diagram add-node architecture.json -t TextNode -n "API Gateway" -x 100 -y 50

# DevOps tools
cli-anything-gnu-mau tools port-scan google.com 443
cli-anything-gnu-mau tools ip-calc 192.168.1.0/24
cli-anything-gnu-mau tools jwt-decode eyJ...
cli-anything-gnu-mau tools hash mypassword -r 100000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GNUMAU_DB_PATH` | Path to Mongita database dir | `./mongita_data` |
| `GNUMAU_STORAGE_PATH` | Path to file storage dir | `./storage` |

## Running Tests

```bash
cd agent-harness
pip install -e .
pip install pytest
python -m pytest cli_anything/gnu_mau/tests/ -v -s
```

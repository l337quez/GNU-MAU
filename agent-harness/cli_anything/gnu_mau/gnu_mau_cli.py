"""
GNU Mau CLI — Main entry point.

A complete CLI harness for the GNU Mau productivity application,
providing full project management, TODO lists, notes, diagrams,
and DevOps tools through a structured command-line interface.

Usage:
    cli-anything-gnu-mau                     # Enter interactive REPL
    cli-anything-gnu-mau --json project list  # JSON output for agents
    cli-anything-gnu-mau project new -n "My Project"
    cli-anything-gnu-mau todo list --project <id>
"""
import os
import sys
import json
import click

from cli_anything.gnu_mau.core import (
    list_projects, get_project, create_project, update_project,
    delete_project, list_info, add_info, delete_info,
)
from cli_anything.gnu_mau.core.todo import (
    list_todos, get_todo, create_todo, update_todo, delete_todo,
)
from cli_anything.gnu_mau.core.notes import (
    list_notes, get_note, create_note, update_note, delete_note, rename_note,
)
from cli_anything.gnu_mau.core.diagrams import (
    list_diagrams, get_diagram, create_diagram, add_node, delete_diagram,
)
from cli_anything.gnu_mau.core.tools import (
    scan_port, calc_ip, decode_jwt, hash_password,
)
from cli_anything.gnu_mau.core.session import (
    get_active_project, set_active_project, get_session_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output(data, as_json):
    """Print *data* as JSON or formatted text."""
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, list):
            for item in data:
                _print_dict(item)
                click.echo()
        elif isinstance(data, dict):
            _print_dict(data)
        else:
            click.echo(data)


def _print_dict(d, indent=0):
    """Pretty-print a dict for humans."""
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            click.echo(f"{prefix}{click.style(str(k), bold=True)}:")
            _print_dict(v, indent + 1)
        elif isinstance(v, list):
            click.echo(f"{prefix}{click.style(str(k), bold=True)}: [{len(v)} items]")
        else:
            click.echo(f"{prefix}{click.style(str(k), bold=True)}: {v}")


def _resolve_project(project_id):
    """Resolve project_id from argument or active session."""
    if project_id:
        return project_id
    active = get_active_project()
    if active:
        return active
    # Try first project as fallback
    projects = list_projects()
    if projects:
        return projects[0]["_id"]
    raise click.ClickException("No project specified and no active project. "
                               "Use --project <id> or `session set <id>`.")


# ---------------------------------------------------------------------------
# Root CLI Group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output in JSON format for machine consumption.")
@click.option("--db-path", default=None, envvar="GNUMAU_DB_PATH",
              help="Path to the Mongita database directory.")
@click.pass_context
def cli(ctx, as_json, db_path):
    """CLI-Anything harness for GNU Mau — Multipurpose Automation Utility.

    Run without arguments to enter the interactive REPL.
    """
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    ctx.obj["db_path"] = db_path

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ---------------------------------------------------------------------------
# Project commands
# ---------------------------------------------------------------------------

@cli.group("project")
@click.pass_context
def project_group(ctx):
    """Manage GNU Mau projects."""
    pass


@project_group.command("list")
@click.pass_context
def project_list(ctx):
    """List all projects."""
    data = list_projects(ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@project_group.command("new")
@click.option("-n", "--name", required=True, help="Project name.")
@click.option("-d", "--description", default="", help="Project description.")
@click.pass_context
def project_new(ctx, name, description):
    """Create a new project."""
    data = create_project(name, description, db_path=ctx.obj.get("db_path"))
    set_active_project(data["_id"])
    _output(data, ctx.obj["as_json"])


@project_group.command("info")
@click.argument("project_id", required=False)
@click.pass_context
def project_info(ctx, project_id):
    """Show project details."""
    pid = _resolve_project(project_id)
    data = get_project(pid, db_path=ctx.obj.get("db_path"))
    if not data:
        raise click.ClickException(f"Project not found: {pid}")
    _output(data, ctx.obj["as_json"])


@project_group.command("update")
@click.argument("project_id", required=False)
@click.option("-n", "--name", default=None, help="New name.")
@click.option("-d", "--description", default=None, help="New description.")
@click.pass_context
def project_update(ctx, project_id, name, description):
    """Update a project's metadata."""
    pid = _resolve_project(project_id)
    data = update_project(pid, name=name, description=description,
                          db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@project_group.command("delete")
@click.argument("project_id")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def project_delete(ctx, project_id, yes):
    """Delete a project."""
    if not yes:
        click.confirm(f"Delete project {project_id}?", abort=True)
    data = delete_project(project_id, db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Info (key-value) commands
# ---------------------------------------------------------------------------

@cli.group("kv")
@click.pass_context
def kv_group(ctx):
    """Manage project key-value info entries."""
    pass


@kv_group.command("list")
@click.option("-p", "--project", "project_id", default=None)
@click.pass_context
def kv_list(ctx, project_id):
    """List all key-value entries for a project."""
    pid = _resolve_project(project_id)
    data = list_info(pid, db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@kv_group.command("add")
@click.option("-p", "--project", "project_id", default=None)
@click.option("-k", "--key", required=True)
@click.option("-v", "--value", required=True)
@click.option("-a", "--action", type=click.Choice(["none", "terminal", "browser"]),
              default="none")
@click.option("-c", "--category", default="")
@click.pass_context
def kv_add(ctx, project_id, key, value, action, category):
    """Add a key-value entry to a project."""
    pid = _resolve_project(project_id)
    act = None if action == "none" else action
    data = add_info(pid, key, value, action=act, category=category,
                    db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@kv_group.command("delete")
@click.option("-p", "--project", "project_id", default=None)
@click.option("-k", "--key", required=True)
@click.pass_context
def kv_delete(ctx, project_id, key):
    """Delete a key-value entry from a project."""
    pid = _resolve_project(project_id)
    data = delete_info(pid, key, db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# TODO commands
# ---------------------------------------------------------------------------

@cli.group("todo")
@click.pass_context
def todo_group(ctx):
    """Manage TODO lists."""
    pass


@todo_group.command("list")
@click.option("-p", "--project", "project_id", default=None)
@click.pass_context
def todo_list_cmd(ctx, project_id):
    """List all TODOs for a project."""
    pid = _resolve_project(project_id)
    data = list_todos(pid, db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@todo_group.command("new")
@click.option("-p", "--project", "project_id", default=None)
@click.option("-t", "--title", default="New TODO")
@click.option("-c", "--content", default="☐ My first task")
@click.pass_context
def todo_new(ctx, project_id, title, content):
    """Create a new TODO."""
    pid = _resolve_project(project_id)
    data = create_todo(pid, title=title, content=content,
                       db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@todo_group.command("show")
@click.argument("todo_id")
@click.pass_context
def todo_show(ctx, todo_id):
    """Show a TODO's details."""
    data = get_todo(todo_id, db_path=ctx.obj.get("db_path"))
    if not data:
        raise click.ClickException(f"TODO not found: {todo_id}")
    _output(data, ctx.obj["as_json"])


@todo_group.command("update")
@click.argument("todo_id")
@click.option("-t", "--title", default=None)
@click.option("-c", "--content", default=None)
@click.pass_context
def todo_update_cmd(ctx, todo_id, title, content):
    """Update a TODO."""
    data = update_todo(todo_id, title=title, content=content,
                       db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


@todo_group.command("delete")
@click.argument("todo_id")
@click.pass_context
def todo_delete_cmd(ctx, todo_id):
    """Delete a TODO."""
    data = delete_todo(todo_id, db_path=ctx.obj.get("db_path"))
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Note commands
# ---------------------------------------------------------------------------

@cli.group("note")
@click.pass_context
def note_group(ctx):
    """Manage Markdown and Rich Text notes."""
    pass


@note_group.command("list")
@click.option("-p", "--project", "project_id", default=None)
@click.pass_context
def note_list_cmd(ctx, project_id):
    """List all notes for a project."""
    pid = _resolve_project(project_id)
    data = list_notes(pid)
    _output(data, ctx.obj["as_json"])


@note_group.command("new")
@click.option("-p", "--project", "project_id", default=None)
@click.option("-n", "--name", required=True, help="Note filename.")
@click.option("--type", "note_type", type=click.Choice(["md", "txt"]),
              default="md", help="Note format.")
@click.pass_context
def note_new(ctx, project_id, name, note_type):
    """Create a new note."""
    pid = _resolve_project(project_id)
    data = create_note(pid, name, note_type=note_type)
    _output(data, ctx.obj["as_json"])


@note_group.command("show")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.pass_context
def note_show(ctx, project_id, filename):
    """Display a note's content."""
    pid = _resolve_project(project_id)
    data = get_note(pid, filename)
    _output(data, ctx.obj["as_json"])


@note_group.command("write")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.option("-c", "--content", required=True, help="Note content.")
@click.pass_context
def note_write(ctx, project_id, filename, content):
    """Overwrite a note's content."""
    pid = _resolve_project(project_id)
    data = update_note(pid, filename, content)
    _output(data, ctx.obj["as_json"])


@note_group.command("delete")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.pass_context
def note_delete_cmd(ctx, project_id, filename):
    """Delete a note."""
    pid = _resolve_project(project_id)
    data = delete_note(pid, filename)
    _output(data, ctx.obj["as_json"])


@note_group.command("rename")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def note_rename(ctx, project_id, old_name, new_name):
    """Rename a note file."""
    pid = _resolve_project(project_id)
    data = rename_note(pid, old_name, new_name)
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Diagram commands
# ---------------------------------------------------------------------------

@cli.group("diagram")
@click.pass_context
def diagram_group(ctx):
    """Manage node-based diagrams."""
    pass


@diagram_group.command("list")
@click.option("-p", "--project", "project_id", default=None)
@click.pass_context
def diagram_list_cmd(ctx, project_id):
    """List all diagrams for a project."""
    pid = _resolve_project(project_id)
    data = list_diagrams(pid)
    _output(data, ctx.obj["as_json"])


@diagram_group.command("new")
@click.option("-p", "--project", "project_id", default=None)
@click.option("-n", "--name", required=True, help="Diagram filename.")
@click.pass_context
def diagram_new(ctx, project_id, name):
    """Create a new empty diagram."""
    pid = _resolve_project(project_id)
    data = create_diagram(pid, name)
    _output(data, ctx.obj["as_json"])


@diagram_group.command("show")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.pass_context
def diagram_show(ctx, project_id, filename):
    """Display a diagram's JSON content."""
    pid = _resolve_project(project_id)
    data = get_diagram(pid, filename)
    _output(data, ctx.obj["as_json"])


@diagram_group.command("add-node")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.option("-t", "--type", "node_type", default="TextNode",
              type=click.Choice(["TextNode", "DatabaseNode",
                                 "DatabaseTableNode", "DiamondNode",
                                 "CircleNode", "GroupNode"]))
@click.option("-n", "--name", default="New Node")
@click.option("-x", default=0.0, type=float)
@click.option("-y", default=0.0, type=float)
@click.pass_context
def diagram_add_node(ctx, project_id, filename, node_type, name, x, y):
    """Add a node to a diagram."""
    pid = _resolve_project(project_id)
    data = add_node(pid, filename, node_type=node_type, name=name, x=x, y=y)
    _output(data, ctx.obj["as_json"])


@diagram_group.command("delete")
@click.option("-p", "--project", "project_id", default=None)
@click.argument("filename")
@click.pass_context
def diagram_delete_cmd(ctx, project_id, filename):
    """Delete a diagram."""
    pid = _resolve_project(project_id)
    data = delete_diagram(pid, filename)
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Tools commands
# ---------------------------------------------------------------------------

@cli.group("tools")
@click.pass_context
def tools_group(ctx):
    """DevOps & networking tools."""
    pass


@tools_group.command("port-scan")
@click.argument("host")
@click.argument("port", type=int)
@click.option("--timeout", default=2, type=int, help="Timeout in seconds.")
@click.pass_context
def tools_port_scan(ctx, host, port, timeout):
    """Scan a TCP port on a host."""
    data = scan_port(host, port, timeout)
    _output(data, ctx.obj["as_json"])


@tools_group.command("ip-calc")
@click.argument("cidr")
@click.pass_context
def tools_ip_calc(ctx, cidr):
    """Calculate network info for a CIDR block."""
    data = calc_ip(cidr)
    _output(data, ctx.obj["as_json"])


@tools_group.command("jwt-decode")
@click.argument("token")
@click.pass_context
def tools_jwt_decode(ctx, token):
    """Decode a JWT payload (no secret needed)."""
    data = decode_jwt(token)
    _output(data, ctx.obj["as_json"])


@tools_group.command("hash")
@click.argument("password")
@click.option("-r", "--rounds", default=1, type=int, help="PBKDF2 rounds.")
@click.pass_context
def tools_hash(ctx, password, rounds):
    """Hash a password with PBKDF2-SHA256."""
    data = hash_password(password, rounds)
    _output(data, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------

@cli.group("session")
@click.pass_context
def session_group(ctx):
    """Manage the CLI session state."""
    pass


@session_group.command("status")
@click.pass_context
def session_status(ctx):
    """Show current session status."""
    data = get_session_status()
    _output(data, ctx.obj["as_json"])


@session_group.command("set")
@click.argument("project_id")
@click.pass_context
def session_set(ctx, project_id):
    """Set the active project for subsequent commands."""
    data = set_active_project(project_id)
    _output({"active_project_id": data["active_project_id"]}, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

@cli.command("repl", hidden=True)
@click.pass_context
def repl(ctx):
    """Enter the interactive REPL."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        has_pt = True
    except ImportError:
        has_pt = False

    click.echo()
    click.echo(click.style("╔══════════════════════════════════════════╗", fg="cyan"))
    click.echo(click.style("║   😸 GNU Mau CLI  — Interactive REPL    ║", fg="cyan"))
    click.echo(click.style("║   Type 'help' for commands, 'q' to quit ║", fg="cyan"))
    click.echo(click.style("╚══════════════════════════════════════════╝", fg="cyan"))
    click.echo()

    if has_pt:
        history_file = os.path.join(os.path.expanduser("~"), ".myapp",
                                    "cli_history")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        session = PromptSession(history=FileHistory(history_file))
    else:
        session = None

    while True:
        try:
            active = get_active_project()
            prompt_str = f"gnu-mau [{active or 'no project'}]> "
            if session:
                line = session.prompt(prompt_str)
            else:
                line = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye! 😸")
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            click.echo("Goodbye! 😸")
            break
        if line.lower() == "help":
            click.echo(cli.get_help(ctx))
            continue

        # Parse and invoke
        import shlex
        try:
            args = shlex.split(line)
        except ValueError as e:
            click.echo(f"Parse error: {e}")
            continue

        # Preserve --json flag from parent
        if ctx.obj.get("as_json") and "--json" not in args:
            args = ["--json"] + args

        try:
            cli.main(args, standalone_mode=False, **ctx.params)
        except click.ClickException as e:
            e.show()
        except SystemExit:
            pass
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()

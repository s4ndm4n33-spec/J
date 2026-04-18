"""
Tool implementations — the agent's hands.
Each tool takes specific args and returns a string result.
All file operations are sandboxed to the workspace directory.
"""

import os
import subprocess
import glob as globmod

# ── Workspace Sandbox ───────────────────────────────────────────
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_workspace"))


def _safe_path(path: str) -> str:
    """Resolve a path within the workspace. Prevents escaping via ../"""
    if os.path.isabs(path):
        resolved = os.path.abspath(path)
    else:
        resolved = os.path.abspath(os.path.join(WORKSPACE, path))
    if not resolved.startswith(WORKSPACE):
        raise PermissionError(f"Access denied: path '{path}' is outside workspace")
    return resolved


# ── Tool Implementations ────────────────────────────────────────

def read_file(path: str) -> str:
    """Read and return file contents."""
    safe = _safe_path(path)
    if not os.path.exists(safe):
        return f"ERROR: File not found: {path}"
    try:
        with open(safe, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Truncate very large files to stay within context limits
        if len(content) > 12000:
            return content[:12000] + f"\n\n... [truncated — file is {len(content)} chars]"
        return content
    except Exception as e:
        return f"ERROR reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file."""
    safe = _safe_path(path)
    os.makedirs(os.path.dirname(safe), exist_ok=True)
    try:
        with open(safe, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote file: {path} ({len(content)} chars)"
    except Exception as e:
        return f"ERROR writing file: {e}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Find and replace text in a file."""
    safe = _safe_path(path)
    if not os.path.exists(safe):
        return f"ERROR: File not found: {path}"
    try:
        with open(safe, "r", encoding="utf-8") as f:
            content = f.read()
        if old_text not in content:
            return f"ERROR: Could not find the text to replace in {path}. Make sure old_text matches exactly."
        new_content = content.replace(old_text, new_text, 1)
        with open(safe, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Edited file: {path} (replaced {len(old_text)} chars with {len(new_text)} chars)"
    except Exception as e:
        return f"ERROR editing file: {e}"


def run_command(command: str) -> str:
    """Execute a shell command inside the workspace."""
    # Block obviously dangerous commands
    blocked = ["rm -rf /", "sudo", "mkfs", ":(){", "dd if="]
    for b in blocked:
        if b in command:
            return f"ERROR: Blocked dangerous command: {command}"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        if not output.strip():
            return "(command completed with no output)"
        # Truncate very long output
        if len(output) > 8000:
            return output[:8000] + f"\n\n... [truncated — {len(output)} chars total]"
        return output.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out (30s limit)"
    except Exception as e:
        return f"ERROR: {e}"


def search_files(pattern: str, path: str = ".") -> str:
    """Search for a pattern in files using grep."""
    safe_dir = _safe_path(path)
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.html",
             "--include=*.css", "--include=*.json", "--include=*.md", "--include=*.txt",
             "--include=*.yaml", "--include=*.yml", "--include=*.toml",
             pattern, safe_dir],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout.strip()
        if not output:
            return f"No matches found for '{pattern}'"
        # Make paths relative to workspace
        output = output.replace(WORKSPACE + "/", "")
        lines = output.split("\n")
        if len(lines) > 50:
            return "\n".join(lines[:50]) + f"\n\n... [{len(lines)} matches total, showing first 50]"
        return output
    except subprocess.TimeoutExpired:
        return "ERROR: Search timed out"
    except Exception as e:
        return f"ERROR: {e}"


def list_directory(path: str = ".") -> str:
    """List files and directories."""
    safe = _safe_path(path)
    if not os.path.exists(safe):
        return f"ERROR: Directory not found: {path}"
    try:
        entries = sorted(os.listdir(safe))
        result = []
        for entry in entries:
            full = os.path.join(safe, entry)
            if os.path.isdir(full):
                result.append(f"  {entry}/")
            else:
                size = os.path.getsize(full)
                result.append(f"  {entry} ({size} bytes)")
        if not result:
            return "(empty directory)"
        return "\n".join(result)
    except Exception as e:
        return f"ERROR: {e}"


# ── Tool Registry ───────────────────────────────────────────────

TOOL_MAP = {
    "read_file": lambda args: read_file(args["path"]),
    "write_file": lambda args: write_file(args["path"], args["content"]),
    "edit_file": lambda args: edit_file(args["path"], args["old_text"], args["new_text"]),
    "run_command": lambda args: run_command(args["command"]),
    "search_files": lambda args: search_files(args["pattern"], args.get("path", ".")),
    "list_directory": lambda args: list_directory(args.get("path", ".")),
}


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by name with given args."""
    if tool_name not in TOOL_MAP:
        return f"ERROR: Unknown tool '{tool_name}'. Available: {', '.join(TOOL_MAP.keys())}"
    try:
        return TOOL_MAP[tool_name](args)
    except KeyError as e:
        return f"ERROR: Missing required argument {e} for tool '{tool_name}'"
    except Exception as e:
        return f"ERROR executing {tool_name}: {e}"

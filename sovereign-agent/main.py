"""
J. — Sovereign Autonomous Coding Agent
Main entry point. Starts the Flask + WebSocket server.

Usage:
    python main.py

Then open http://localhost:5000 in your browser.
"""

import os
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from core.agent import Agent
from core.tools import run_command

# ── App Setup ───────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Agent Instance ──────────────────────────────────────────────
# Create agent with a callback that emits events to the connected UI
agent = None
agent_lock = threading.Lock()


def create_agent(model: str = "brain"):
    """Create a new agent instance wired to Socket.IO events."""

    def on_event(event_type, data):
        socketio.emit(event_type, data)

    return Agent(model=model, on_event=on_event)


# ── Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Socket Events ───────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    global agent
    if agent is None:
        agent = create_agent()
    emit("status", {"status": "connected"})


@socketio.on("user_message")
def on_user_message(data):
    global agent
    content = data.get("content", "").strip()
    if not content:
        return

    if agent is None:
        agent = create_agent()

    def run_agent():
        try:
            agent.run(content)
        except Exception as e:
            socketio.emit("error", {"content": f"Agent error: {str(e)}"})
            socketio.emit("assistant_message", {"content": f"Something went wrong: {str(e)}"})

    # Run agent in a background thread so the socket isn't blocked
    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()


@socketio.on("shell_command")
def on_shell_command(data):
    """Direct shell command execution (! prefix in UI)."""
    command = data.get("command", "").strip()
    if not command:
        return

    def run_shell():
        try:
            result = run_command(command)
            socketio.emit("shell_result", {"result": result})
        except Exception as e:
            socketio.emit("error", {"content": f"Shell error: {str(e)}"})

    thread = threading.Thread(target=run_shell, daemon=True)
    thread.start()


@socketio.on("reset")
def on_reset():
    global agent
    agent = create_agent()
    emit("reset", {})


@socketio.on("update_settings")
def on_update_settings(data):
    global agent
    model = data.get("model", "phi3")
    ollama_url = data.get("ollama_url", "")

    if ollama_url:
        import core.llm as llm_module
        llm_module.OLLAMA_URL = ollama_url

    agent = create_agent(model=model)
    emit("status", {"status": "settings_updated"})


# ── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    workspace = os.path.join(os.path.dirname(__file__), "agent_workspace")
    os.makedirs(workspace, exist_ok=True)

    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║  J. — Sovereign Autonomous Coding Agent  ║")
    print("  ╠══════════════════════════════════════════╣")
    print("  ║                                          ║")
    print("  ║   Local:   http://localhost:5000          ║")
    print("  ║   Network: http://0.0.0.0:5000           ║")
    print("  ║                                          ║")
    print("  ║   Open in browser or on your phone       ║")
    print("  ║   (same WiFi network)                    ║")
    print("  ║                                          ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)

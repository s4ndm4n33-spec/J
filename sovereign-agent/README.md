# J. — Sovereign Autonomous Coding Agent

A fully local, zero-dependency AI coding agent powered by Phi-3 through Ollama.
No cloud APIs. No subscriptions. No phoning home. Your machine is the entire stack.

## Features

- **ReAct Agent Loop** — J. thinks, acts, observes, and iterates until the task is done
- **6 Built-in Tools** — read/write/edit files, run shell commands, search code, explore directories
- **Hybrid Shell** — chat with J. in natural language OR run terminal commands with `!` prefix
- **Sleek Web UI** — dark theme, real-time streaming, works on desktop and mobile
- **PWA Ready** — install on your phone's home screen for a native app experience
- **Fully Sovereign** — runs 100% local on your hardware, zero internet required

## Prerequisites

1. **Python 3.9+**
2. **Ollama** installed and running:
   ```bash
   # Install: https://ollama.ai
   ollama pull phi3
   ollama serve
   ```

## Quick Start

```bash
# Clone or copy the project
cd sovereign-agent

# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running with Phi-3
ollama serve  # (in another terminal)

# Launch J.
python main.py
```

Then open **http://localhost:5000** in your browser.

## Access from Your Phone

**Same WiFi:** Open `http://<your-pc-ip>:5000` on your phone's browser.

Find your PC's IP:
```bash
# macOS
ipconfig getifaddr en0

# Windows
ipconfig

# Linux
hostname -I
```

**From Anywhere:** Use ngrok for a public URL:
```bash
pip install ngrok
ngrok http 5000
```

**Install as App:** In your phone's browser, tap "Add to Home Screen" — J. becomes a fullscreen app.

## Usage

### Chat Mode
Just type naturally:
```
> Build a Flask API with user authentication
> Fix the bug in app.py — the login route returns 500
> Add unit tests for the database module
```

### Shell Mode
Prefix with `!` to run commands directly:
```
> !ls -la
> !python app.py
> !git status
> !pip install requests
```

## Project Structure

```
sovereign-agent/
├── main.py              # Entry point — Flask + WebSocket server
├── requirements.txt     # Python dependencies
├── AGENTS.md            # Project instructions template (for J. to read)
├── core/
│   ├── agent.py         # ReAct agent loop
│   ├── llm.py           # Ollama API interface
│   ├── memory.py        # Conversation history + context management
│   ├── tools.py         # Tool implementations (file ops, shell, search)
│   └── prompts.py       # System prompt + tool definitions
├── static/
│   ├── css/style.css    # Dark theme UI
│   ├── js/app.js        # WebSocket client + UI logic
│   └── manifest.json    # PWA manifest
├── templates/
│   └── index.html       # Main UI page
└── agent_workspace/     # Sandboxed directory where J. writes code
```

## How It Works

J. uses the same architecture as Claude Code and Codex:

1. You send a message
2. J. thinks about what to do
3. J. calls a tool (read file, write code, run command, etc.)
4. J. observes the result
5. Repeat steps 2-4 until the task is done
6. J. sends you the final response

All tool calls are sandboxed to the `agent_workspace/` directory.

## Configuration

Click the ⚙ button in the UI to change:
- **Model** — switch to any Ollama model (e.g., `phi3:medium`, `codellama`, `mistral`)
- **Ollama URL** — point to a different Ollama instance

## Tips for Best Results

- **Be specific** — "Add a /users endpoint that returns JSON" > "make an API"
- **Break big tasks into steps** — J. handles focused tasks best
- **Let J. iterate** — if something fails, J. reads the error and tries again
- **Use AGENTS.md** — drop project-specific instructions in your workspace
- **Check the workspace** — your code lives in `agent_workspace/`

## Customization

### Persona
Edit the system prompt in `core/prompts.py` to change J.'s personality.

### Tools
Add new tools in `core/tools.py` — just add a function and register it in `TOOL_MAP`.

### Model
Any Ollama model works. Larger models = better reasoning but slower:
- `phi3` — fast, good for focused tasks (default)
- `phi3:medium` — better reasoning
- `codellama:13b` — strong at code generation
- `deepseek-coder-v2` — excellent coder, heavier

## License

Do whatever you want with it. It's your agent.

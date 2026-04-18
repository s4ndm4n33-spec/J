// ── J. — Sovereign Agent UI ──────────────────────────────────

const socket = io();
const output = document.getElementById('output');
const input = document.getElementById('input');
const btnSend = document.getElementById('btn-send');
const btnClear = document.getElementById('btn-clear');
const btnSettings = document.getElementById('btn-settings');
const statusText = document.getElementById('status-text');
const settingsModal = document.getElementById('settings-modal');

let busy = false;
let thinkingEl = null;

// ── Helpers ──────────────────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        output.scrollTop = output.scrollHeight;
    });
}

function setStatus(text, active = false) {
    statusText.textContent = text;
    statusText.classList.toggle('active', active);
}

function setBusy(state) {
    busy = state;
    btnSend.disabled = state;
    input.disabled = state;
    if (!state) input.focus();
}

function removeWelcome() {
    const welcome = output.querySelector('.welcome-msg');
    if (welcome) welcome.remove();
}

function removeThinking() {
    if (thinkingEl) {
        thinkingEl.remove();
        thinkingEl = null;
    }
}

function addMessage(type, label, content) {
    removeWelcome();
    removeThinking();

    const msg = document.createElement('div');
    msg.className = `msg msg-${type}`;

    const labelEl = document.createElement('div');
    labelEl.className = 'msg-label';
    labelEl.textContent = label;

    const contentEl = document.createElement('div');
    contentEl.className = 'msg-content';
    contentEl.textContent = content;

    msg.appendChild(labelEl);
    msg.appendChild(contentEl);
    output.appendChild(msg);
    scrollToBottom();
    return msg;
}

function showThinking(iteration) {
    removeThinking();
    removeWelcome();

    const msg = document.createElement('div');
    msg.className = 'msg msg-thinking';

    const label = document.createElement('div');
    label.className = 'msg-label';
    label.textContent = 'J.';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.innerHTML = `thinking (step ${iteration})<span class="thinking-dots"></span>`;

    msg.appendChild(label);
    msg.appendChild(content);
    output.appendChild(msg);
    thinkingEl = msg;
    scrollToBottom();
}

// ── Format tool call for display ─────────────────────────────

function formatToolCall(tool, args) {
    let display = tool + '(';
    const parts = [];
    for (const [k, v] of Object.entries(args || {})) {
        let val = typeof v === 'string' ? v : JSON.stringify(v);
        // Truncate long values
        if (val.length > 200) val = val.substring(0, 200) + '…';
        parts.push(`${k}: ${val}`);
    }
    display += parts.join(', ') + ')';
    return display;
}

// ── Socket Events ────────────────────────────────────────────

socket.on('connect', () => setStatus('connected'));
socket.on('disconnect', () => setStatus('disconnected'));

socket.on('thinking', (data) => {
    setStatus('thinking', true);
    showThinking(data.iteration);
});

socket.on('tool_call', (data) => {
    setStatus(`tool: ${data.tool}`, true);
    removeThinking();
    addMessage('tool-call', `⚡ ${data.tool}`, formatToolCall(data.tool, data.args));
});

socket.on('tool_result', (data) => {
    addMessage('tool-result', `↳ ${data.tool} result`, data.result);
});

socket.on('tool_error', (data) => {
    addMessage('error', '✗ tool error', data.error);
});

socket.on('assistant_message', (data) => {
    setStatus('ready');
    removeThinking();
    addMessage('assistant', 'J.', data.content);
    setBusy(false);
});

socket.on('shell_result', (data) => {
    setStatus('ready');
    removeThinking();
    addMessage('shell', '$ shell', data.result);
    setBusy(false);
});

socket.on('error', (data) => {
    setStatus('error');
    removeThinking();
    addMessage('error', '✗ error', data.content || data.message || 'Unknown error');
    setBusy(false);
});

socket.on('reset', () => {
    output.innerHTML = '';
    setStatus('ready');
    setBusy(false);
});

// ── Send Message ─────────────────────────────────────────────

function send() {
    const text = input.value.trim();
    if (!text || busy) return;

    input.value = '';
    autoResize();

    // Shell command: prefix with !
    if (text.startsWith('!')) {
        const cmd = text.substring(1).trim();
        addMessage('user', '$ you', cmd);
        setBusy(true);
        setStatus('running command', true);
        socket.emit('shell_command', { command: cmd });
        return;
    }

    // Regular message to agent
    addMessage('user', 'you', text);
    setBusy(true);
    setStatus('thinking', true);
    socket.emit('user_message', { content: text });
}

// ── Input Handling ───────────────────────────────────────────

function autoResize() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

input.addEventListener('input', autoResize);

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
    }
});

btnSend.addEventListener('click', send);

// ── Clear / Reset ────────────────────────────────────────────

btnClear.addEventListener('click', () => {
    socket.emit('reset');
    output.innerHTML = `
        <div class="welcome-msg">
            <span class="welcome-logo">J<span class="logo-dot">.</span></span>
            <p>Sovereign Autonomous Coding Agent</p>
            <p class="welcome-sub">Type a message to chat, or prefix with <code>!</code> to run a shell command directly.</p>
        </div>`;
    setStatus('ready');
    setBusy(false);
});

// ── Settings Modal ───────────────────────────────────────────

btnSettings.addEventListener('click', () => settingsModal.classList.remove('hidden'));
document.getElementById('settings-close').addEventListener('click', () => settingsModal.classList.add('hidden'));
document.getElementById('settings-save').addEventListener('click', () => {
    const model = document.getElementById('setting-model').value.trim();
    const url = document.getElementById('setting-url').value.trim();
    socket.emit('update_settings', { model, ollama_url: url });
    settingsModal.classList.add('hidden');
    setStatus('settings saved');
    setTimeout(() => setStatus('ready'), 2000);
});

// Close modal on backdrop click
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) settingsModal.classList.add('hidden');
});

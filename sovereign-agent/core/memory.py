"""
Conversation memory — tracks the full interaction history.
Handles context compaction so Phi-3 stays within its sweet spot.
"""

import json
import time
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    role: str  # "user", "assistant", "tool_call", "tool_result", "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)  # tool name, args, etc.


class Memory:
    def __init__(self, max_entries: int = 100, max_prompt_chars: int = 6000):
        self.entries: list[MemoryEntry] = []
        self.max_entries = max_entries
        self.max_prompt_chars = max_prompt_chars

    def add(self, role: str, content: str, metadata: dict = None):
        """Add an entry to memory."""
        self.entries.append(MemoryEntry(
            role=role,
            content=content,
            metadata=metadata or {},
        ))
        # Hard cap: drop oldest entries beyond limit
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def build_prompt(self, system_prompt: str, user_message: str) -> str:
        """
        Build the full prompt for the model.
        Uses a simple format that Phi-3 handles well.
        Compacts older entries if the prompt gets too long.
        """
        parts = []

        # Add conversation history
        for entry in self.entries:
            if entry.role == "user":
                parts.append(f"User: {entry.content}")
            elif entry.role == "assistant":
                parts.append(f"You: {entry.content}")
            elif entry.role == "tool_call":
                tool = entry.metadata.get("tool", "?")
                parts.append(f"You: {entry.content}")
            elif entry.role == "tool_result":
                tool = entry.metadata.get("tool", "?")
                parts.append(f"[Tool result for {tool}]: {entry.content}")

        # Add the new user message
        parts.append(f"User: {user_message}")
        parts.append("You:")

        history = "\n\n".join(parts)

        # Compact if too long: keep system prompt + last N entries
        while len(history) > self.max_prompt_chars and len(parts) > 4:
            parts.pop(0)  # Remove oldest entry
            history = "\n\n".join(parts)

        return history

    def build_chat_messages(self, system_prompt: str, user_message: str = None) -> list[dict]:
        """
        Build messages array for Ollama's /api/chat endpoint.
        This is the preferred format for Phi-3.
        """
        messages = [{"role": "system", "content": system_prompt}]

        for entry in self.entries:
            if entry.role == "user":
                messages.append({"role": "user", "content": entry.content})
            elif entry.role in ("assistant", "tool_call"):
                messages.append({"role": "assistant", "content": entry.content})
            elif entry.role == "tool_result":
                tool = entry.metadata.get("tool", "tool")
                messages.append({
                    "role": "user",
                    "content": f"[Tool result for {tool}]: {entry.content}",
                })

        if user_message:
            messages.append({"role": "user", "content": user_message})

        # Compact: trim from the front (after system) if too many chars
        total = sum(len(m["content"]) for m in messages)
        while total > self.max_prompt_chars and len(messages) > 3:
            removed = messages.pop(1)  # Remove oldest non-system message
            total -= len(removed["content"])

        return messages

    def clear(self):
        """Reset memory."""
        self.entries.clear()

    def get_history_for_ui(self) -> list[dict]:
        """Return history formatted for the UI."""
        result = []
        for entry in self.entries:
            result.append({
                "role": entry.role,
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp,
            })
        return result

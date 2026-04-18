"""
The Agent — core ReAct loop.
Think → Tool Call → Observe → Repeat → Done.
"""

import json
import re
import time
from typing import Callable, Optional

from core.llm import chat
from core.memory import Memory
from core.tools import execute_tool, WORKSPACE
from core.prompts import SYSTEM_PROMPT, VALID_TOOLS


class Agent:
    def __init__(
        self,
        model: str = "phi3",
        max_iterations: int = 20,
        on_event: Optional[Callable] = None,
    ):
        self.model = model
        self.max_iterations = max_iterations
        self.memory = Memory()
        self.on_event = on_event or (lambda *a, **kw: None)  # UI callback

    def _emit(self, event_type: str, data: dict):
        """Send an event to the UI."""
        self.on_event(event_type, data)

    def _parse_response(self, raw: str) -> dict:
        """
        Parse the model's response. Expects JSON but handles common issues
        that small models produce (markdown wrapping, extra text, etc.)
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        # Try direct JSON parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from mixed text
        # Look for the first { ... } block
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # If all parsing fails, treat as a plain message
        return {"message": text}

    def run(self, user_input: str) -> str:
        """
        Main agent loop. Takes a user message, runs the ReAct loop,
        returns the final response.
        """
        self.memory.add("user", user_input)
        self._emit("user_message", {"content": user_input})

        for iteration in range(self.max_iterations):
            # Build conversation and call the model
            messages = self.memory.build_chat_messages(SYSTEM_PROMPT)
            self._emit("thinking", {"iteration": iteration + 1})

            raw_response = chat(messages, model=self.model)

            if not raw_response:
                self._emit("error", {"content": "Empty response from model"})
                break

            parsed = self._parse_response(raw_response)

            # ── Case 1: Tool call ──────────────────────────────
            if "tool" in parsed:
                tool_name = parsed["tool"]
                tool_args = parsed.get("args", {})

                # Validate tool name
                if tool_name not in VALID_TOOLS:
                    error_msg = f"Unknown tool '{tool_name}'. Available: {', '.join(VALID_TOOLS)}"
                    self.memory.add("tool_result", error_msg, {"tool": tool_name})
                    self._emit("tool_error", {"tool": tool_name, "error": error_msg})
                    continue

                # Log the tool call
                self.memory.add("tool_call", raw_response, {"tool": tool_name, "args": tool_args})
                self._emit("tool_call", {"tool": tool_name, "args": tool_args})

                # Execute the tool
                result = execute_tool(tool_name, tool_args)

                # Log the result
                self.memory.add("tool_result", result, {"tool": tool_name})
                self._emit("tool_result", {"tool": tool_name, "result": result})

                # Continue the loop — let the model decide next step
                continue

            # ── Case 2: Message to user (done) ─────────────────
            if "message" in parsed:
                message = parsed["message"]
                self.memory.add("assistant", message)
                self._emit("assistant_message", {"content": message})
                return message

            # ── Case 3: Unparseable — treat as message ─────────
            self.memory.add("assistant", raw_response)
            self._emit("assistant_message", {"content": raw_response})
            return raw_response

        # Max iterations reached
        timeout_msg = "I've reached my iteration limit. Here's where I got to — let me know if you want me to continue."
        self.memory.add("assistant", timeout_msg)
        self._emit("assistant_message", {"content": timeout_msg})
        return timeout_msg

    def reset(self):
        """Clear memory and start fresh."""
        self.memory.clear()
        self._emit("reset", {})

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    """Small amount of session state for multi-turn conversations."""

    pending_intent: str | None = None
    email: str | None = None
    order_number: str | None = None
    generated_codes: dict[str, str] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)

    def remember_user_message(self, message: str) -> None:
        self.history.append({"role": "user", "content": message})

    def remember_assistant_message(self, message: str) -> None:
        self.history.append({"role": "assistant", "content": message})

    def conversation_text(self, max_turns: int = 8) -> str:
        recent = self.history[-max_turns:]
        lines = []
        for item in recent:
            role = "Customer" if item["role"] == "user" else "Agent"
            lines.append(f"{role}: {item['content']}")
        return "\n".join(lines)


@dataclass(frozen=True)
class AgentDecision:
    intent: str
    facts: dict[str, Any]

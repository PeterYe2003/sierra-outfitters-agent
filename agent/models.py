from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    """Session state for a multi-turn conversation."""

    # Current unfinished task, if any.
    pending_intent: str | None = None

    # User details collected from the conversation.
    email: str | None = None
    order_number: str | None = None

    # Discount codes already generated this session.
    generated_codes: dict[str, str] = field(default_factory=dict)

    # Recent conversation messages.
    history: list[dict[str, str]] = field(default_factory=list)

    def remember_user_message(self, message: str) -> None:
        # Save a customer message.
        self.history.append({"role": "user", "content": message})

    def remember_assistant_message(self, message: str) -> None:
        # Save an agent message.
        self.history.append({"role": "assistant", "content": message})

    def conversation_text(self, max_turns: int = 8) -> str:
        # Format the most recent messages as a readable transcript.
        recent = self.history[-max_turns:]
        lines = []

        for item in recent:
            role = "Customer" if item["role"] == "user" else "Agent"
            lines.append(f"{role}: {item['content']}")

        return "\n".join(lines)


@dataclass(frozen=True)
class AgentDecision:
    # The intent chosen by the agent.
    intent: str

    # Structured facts used to generate the final response.
    facts: dict[str, Any]
from __future__ import annotations

import argparse
from pathlib import Path

from agent.llm import DEFAULT_MODEL, generate_response
from agent.models import ConversationState
from agent.router import handle_message
from agent.tools import load_json

ROOT = Path(__file__).resolve().parent
ORDERS_PATH = ROOT / "data" / "CustomerOrders.json"
PRODUCTS_PATH = ROOT / "data" / "ProductCatalog.json"


def run_chat(model: str = DEFAULT_MODEL) -> None:
    orders = load_json(ORDERS_PATH)
    products = load_json(PRODUCTS_PATH)
    state = ConversationState()

    print("Sierra Outfitters Agent")
    print("Type 'exit' or 'quit' to leave base camp.\n")

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAgent: Safe travels. Onward into the unknown!")
            break

        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit"}:
            print("Agent: Safe travels. Onward into the unknown!")
            break

        state.remember_user_message(user_message)
        decision = handle_message(user_message, state, orders, products)
        response = generate_response(
            conversation=state.conversation_text(),
            facts=decision.facts,
            model=model,
        )
        state.remember_assistant_message(response)
        print(f"Agent: {response}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sierra Outfitters terminal agent")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Defaults to {DEFAULT_MODEL}.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_chat(model=args.model)

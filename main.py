from __future__ import annotations

import argparse
from pathlib import Path

from agent.llm import DEFAULT_MODEL, generate_response, get_model
from agent.models import ConversationState
from agent.router import handle_message
from agent.tools import load_json

# Setup paths to data files.
ROOT = Path(__file__).resolve().parent
ORDERS_PATH = ROOT / "data" / "CustomerOrders.json"
PRODUCTS_PATH = ROOT / "data" / "ProductCatalog.json"


def run_chat(model: str | None = None) -> None:
    # Load initial data and initialize conversation state.
    orders = load_json(ORDERS_PATH)
    products = load_json(PRODUCTS_PATH)
    state = ConversationState()

    print("Sierra Outfitters Agent")
    print("Type 'exit' or 'quit' to leave base camp.\n")
    print("Hi there! Welcome to Sierra Outfitters. How can I help you on your next adventure?\n")
    # Main interaction loop.
    while True:
        try:
            # Get input from the user.
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handle exit via keyboard shortcut.
            print("\nAgent: Safe travels. Onward into the unknown!")
            break

        # Basic input validation.
        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit"}:
            print("Agent: Safe travels. Onward into the unknown!")
            break

        # 1. Update session state with the new user message.
        state.remember_user_message(user_message)

        # 2. Process the message to find the intent and gather facts.
        decision = handle_message(user_message, state, orders, products)

        # 3. Generate a natural language response based on those facts.
        response = generate_response(
            conversation=state.conversation_text(),
            facts=decision.facts,
            model=model,
        )

        # 4. Save and display the response.
        state.remember_assistant_message(response)
        print(f"Agent: {response}\n")


def parse_args() -> argparse.Namespace:
    # Setup command line arguments.
    parser = argparse.ArgumentParser(description="Sierra Outfitters terminal agent")
    parser.add_argument(
        "--model",
        default=None,
        help=f"OpenAI model to use. Defaults to {get_model()}.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Start the agent.
    args = parse_args()
    run_chat(model=args.model)
    
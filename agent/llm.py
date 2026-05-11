from __future__ import annotations

import json
import os
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI

from .prompts import RESPONSE_PROMPT, SYSTEM_PROMPT

load_dotenv()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def format_facts(facts: dict[str, Any]) -> str:
    return json.dumps(facts, indent=2, ensure_ascii=False)


def generate_response(
    conversation: str,
    facts: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a polished customer-facing response.

    Falls back to deterministic text if OPENAI_API_KEY is not available, so the
    demo remains usable without network/API setup.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return deterministic_fallback(facts)

    client = OpenAI(api_key=api_key)
    prompt = RESPONSE_PROMPT.format(
        conversation=conversation or "No prior conversation.",
        facts=format_facts(facts),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    content = response.choices[0].message.content
    return content.strip() if content else deterministic_fallback(facts)


def deterministic_fallback(facts: dict[str, Any]) -> str:
    """Reliable non-LLM backup for local demos and tests."""
    status = facts.get("status")

    if status == "missing_information":
        missing = facts.get("missing", [])
        if len(missing) == 2:
            return "Happy to help you track that trail marker 🏔️ Could you share the email and order number for the order?"
        return f"Happy to help you summit this. Could you share your {missing[0]}?"

    if status == "not_found":
        return (
            "I couldn't find a matching order for that email and order number. "
            "Could you double-check both and send them again?"
        )

    if status == "found":
        order = facts["order"]
        product_names = ", ".join(
            p.get("ProductName", p.get("SKU", "Unknown product"))
            for p in order.get("ProductDetails", [])
        )
        lines = [
            f"Trail update: order {order['OrderNumber']} is currently **{order['Status']}**.",
            f"Items: {product_names}.",
        ]
        if order.get("TrackingLink"):
            lines.append(f"USPS tracking: {order['TrackingLink']}")
        elif order.get("Status") == "fulfilled":
            lines.append("It has been fulfilled, but tracking is not available yet.")
        elif order.get("Status") == "error":
            lines.append("I’m sorry, there appears to be an issue with the order record. Please contact support so we can help get this expedition back on route.")
        return "\n".join(lines)

    if status == "ok" and "products" in facts:
        products = facts["products"]
        if not products:
            return "I didn’t find a perfect match, but I can help you pick trail-ready gear if you tell me more about the adventure."
        lines = ["Here are my top trail-ready picks:"]
        for p in products:
            lines.append(
                f"- {p['ProductName']} ({p['SKU']}): {p['Inventory']} in stock. {p['Description']}"
            )
        lines.append("Onward into the unknown!")
        return "\n".join(lines)

    if status == "eligible":
        return (
            f"You caught the sunrise window 🌄 Your Early Risers code is **{facts['code']}** "
            f"for {facts['discount_percent']}% off. Onward into the unknown!"
        )

    if status == "not_eligible_now":
        return (
            "The Early Risers Promotion is only available from "
            f"{facts['valid_window']}. Check back during that sunrise window!"
        )

    if status == "no_explicit_early_risers_request":
        return (
            "We do have an Early Risers Promotion, but I can only generate that code "
            "when you explicitly request it during 8:00-10:00 AM Pacific Time."
        )

    return (
        "Happy to help from base camp 🏔️ I can assist with order tracking, "
        "product recommendations, or the Early Risers Promotion."
    )

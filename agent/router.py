from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import AgentDecision, ConversationState
from .tools import (
    enrich_order_products,
    extract_email,
    extract_order_number,
    generate_discount_code,
    is_early_risers_request,
    is_early_risers_window,
    lookup_order,
    search_products,
)

# Keywords that suggest the user is asking about an order.
ORDER_KEYWORDS = ["order", "tracking", "track", "package", "shipment", "shipped", "delivered"]

# Keywords that suggest the user wants a product recommendation.
PRODUCT_KEYWORDS = [
    "recommend", "recommendation", "product", "gear", "catalog", "hiking", "snow",
    "ski", "skis", "backpack", "drink", "snack", "food", "high-tech", "stealth",
    "cloak", "jetpack", "plane", "shoes", "lamp", "trail", "adventure",
]

# Keywords that suggest the user is asking about discounts in general.
DISCOUNT_KEYWORDS = ["discount", "promo", "promotion", "coupon", "code"]


def classify_intent(message: str, state: ConversationState) -> str:
    #Could also use LLM to classify intent,
    lower = message.lower()

    if is_early_risers_request(message):
        return "early_risers"

    if state.pending_intent == "order_status":
        return "order_status"

    if any(word in lower for word in ORDER_KEYWORDS):
        return "order_status"

    if any(word in lower for word in PRODUCT_KEYWORDS):
        return "product_recommendation"

    # Vague discount requests should not trigger Early Risers unless explicitly named.
    if any(word in lower for word in DISCOUNT_KEYWORDS):
        return "general_discount"

    return "general"


def handle_message(
    message: str,
    state: ConversationState,
    orders: list[dict[str, Any]],
    products: list[dict[str, Any]],
    now: datetime | None = None,
) -> AgentDecision:

    # Figure out what the user is asking for.
    intent = classify_intent(message, state)

    # Try to extract an email and order number from the message.
    found_email = extract_email(message)
    found_order = extract_order_number(message)

    # Store the email or order number in conversation state if one was found.
    if found_email:
        state.email = found_email
    if found_order:
        state.order_number = found_order

    # Handle order tracking/status requests.
    if intent == "order_status":
        state.pending_intent = "order_status"
        missing = []
        if not state.email:
            missing.append("email")
        if not state.order_number:
            missing.append("order number")

        if missing:
            return AgentDecision(
                intent=intent,
                facts={
                    "status": "missing_information",
                    "missing": missing,
                    "instruction": "Ask for the missing order lookup information. Ask only one focused question.",
                },
            )

        order = lookup_order(orders, state.email, state.order_number)
        state.pending_intent = None
        if not order:
            return AgentDecision(
                intent=intent,
                facts={
                    "status": "not_found",
                    "email": state.email,
                    "order_number": state.order_number,
                    "instruction": "Say no matching order was found and ask the customer to double-check the email and order number.",
                },
            )

        enriched = enrich_order_products(order, products)
        return AgentDecision(
            intent=intent,
            facts={
                "status": "found",
                "order": enriched,
                "instruction": "Provide the order status and tracking link if present. For fulfilled orders without tracking, explain that tracking is not available yet. For error status, apologize and recommend contacting support.",
            },
        )

    if intent == "product_recommendation":
        matches = search_products(products, message)
        return AgentDecision(
            intent=intent,
            facts={
                "status": "ok",
                "products": matches,
                "instruction": "Recommend the best matching products using product name, SKU, inventory, and a brief reason. If matches are weak, say these are the closest trail-ready options.",
            },
        )

    # Handle explicit Early Risers discount requests.
    if intent == "early_risers":
        if is_early_risers_window(now):
            # Session-level uniqueness: reuse a code for the same email if known.
            code_key = state.email or "anonymous"
            code = state.generated_codes.get(code_key)
            if not code:
                code = generate_discount_code()
                state.generated_codes[code_key] = code
            return AgentDecision(
                intent=intent,
                facts={
                    "status": "eligible",
                    "discount_percent": 10,
                    "code": code,
                    "instruction": "Give the customer the unique Early Risers code and mention it is for 10% off.",
                },
            )
        return AgentDecision(
            intent=intent,
            facts={
                "status": "not_eligible_now",
                "valid_window": "8:00 AM to 10:00 AM Pacific Time",
                "instruction": "Politely say the Early Risers Promotion is only available during the valid Pacific Time window.",
            },
        )
        
    # Handle vague discount requests.
    # I interpreted the intent of the company to not tell the customer about the promo if it is not explicitly asked for.
    if intent == "general_discount":
        return AgentDecision(
            intent=intent,
            facts={
                "status": "no_explicit_early_risers_request",
                "instruction": "Do not generate a code.",
                #Explain that the Early Risers Promotion is available only when explicitly requested during 8:00-10:00 AM PT.
            },
        )

    # Default/general response.
    # Used when the user asks something outside the supported flows.
    return AgentDecision(
        intent=intent,
        facts={
            "status": "general",
            "instruction": "Answer conversationally as Sierra Outfitters. If the request is outside supported capabilities, say you can help with order tracking, product recommendations, or promotions.",
        },
    )

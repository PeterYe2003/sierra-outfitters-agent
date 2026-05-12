from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


# Finds email addresses in text.
# Example: "peter@example.com"
EMAIL_RE = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)

# Finds order numbers that look like W123, W-123, #W123, # W - 123, etc.
ORDER_RE = re.compile(
    r"#?\s*[Ww]\s*-?\s*\d+",
    re.IGNORECASE,
)

# Finds simple word/number chunks in text.
# Example: "snow boots!" becomes ["snow", "boots"]
WORD_RE = re.compile(r"[a-z0-9]+")


# Words that are too common to be useful in product search.
# These get removed from user queries.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "for", "from", "i",
    "in", "is", "it", "me", "my", "of", "on", "or", "please", "something",
    "that", "the", "to", "what", "with", "you", "your", "need", "want", "looking",
    "recommend", "recommendation", "product", "gear", "item", "items",
}


def load_json(path: Path) -> list[dict[str, Any]]:
    # Open a JSON file and load it into Python.
    # This assumes the JSON file contains a list of dictionaries.
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_order_number(order_number: str) -> str:
    # Look for the numeric part of the order number.
    # Example: "#W-7" -> finds "7"
    num_match = re.search(r"\d+", order_number)

    if num_match:
        # Pad the number to at least 3 digits.
        # Example: "7" -> "007", "42" -> "042"
        num_str = num_match.group(0).zfill(3)

        # Return the order number in one consistent format.
        return f"#W{num_str}"

    # Fallback if no digits are found:
    # trim spaces and convert to uppercase.
    cleaned = order_number.strip().upper()

    # Make sure it starts with "#".
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"

    return cleaned


def extract_email(message: str) -> str | None:
    # Search the message for the first email address.
    match = EMAIL_RE.search(message)

    # If found, return it lowercase. Otherwise return None.
    return match.group(0).lower() if match else None


def extract_order_number(message: str) -> str | None:
    # First try to find a W-style order number, like "#W123" or "W-123".
    match = ORDER_RE.search(message)

    if match:
        return normalize_order_number(match.group(0))

    # If that fails, try to find phrases like:
    # "order 123"
    # "order number 123"
    # "order #123"
    context_match = re.search(
        r"order\s*(?:number|#)?\s*(\d+)",
        message,
        re.IGNORECASE,
    )

    if context_match:
        return normalize_order_number(context_match.group(1))

    # No order number was found.
    return None


def lookup_order(
    orders: list[dict[str, Any]],
    email: str,
    order_number: str,
) -> dict[str, Any] | None:
    # Normalize the user-provided email and order number before comparing.
    normalized_email = email.strip().lower()
    normalized_order = normalize_order_number(order_number)

    # Check every order in the order list.
    for order in orders:
        # Match both the email and the normalized order number.
        if (
            order.get("Email", "").lower() == normalized_email
            and normalize_order_number(order.get("OrderNumber", "")) == normalized_order
        ):
            # Copy the order so we do not modify the original dictionary.
            result = dict(order)

            # If the order has a tracking number, create a USPS tracking link.
            tracking_number = result.get("TrackingNumber")
            result["TrackingLink"] = (
                f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
                if tracking_number
                else None
            )

            return result

    # No matching order found.
    return None


def products_by_sku(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    # Convert a list of products into a dictionary keyed by SKU.
    # This makes it easier to quickly look up a product by its SKU.
    return {p["SKU"]: p for p in products}


def enrich_order_products(
    order: dict[str, Any],
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    # Build a SKU -> product lookup dictionary.
    sku_to_product = products_by_sku(products)

    # Copy the order so the original order is not changed.
    enriched = dict(order)

    # Add a new field with full product details for every SKU in the order.
    # If a SKU is missing from the product catalog, use a fallback value.
    enriched["ProductDetails"] = [
        sku_to_product.get(sku, {"SKU": sku, "ProductName": "Unknown product"})
        for sku in order.get("ProductsOrdered", [])
    ]

    return enriched


def _normalize_term(term: str) -> str:
    # Tiny normalization for common catalog queries without adding dependencies.

    # Treat "snowy" as "snow" so searches like "snowy jacket" match snow products.
    if term == "snowy":
        return "snow"

    # Remove "ing" from longer words.
    # Example: "hiking" -> "hik"
    # This is simple and not perfect, but good enough for a small search demo.
    if term.endswith("ing") and len(term) > 5:
        return term[:-3]

    # Remove plural "s" from longer words.
    # Example: "boots" -> "boot"
    if term.endswith("s") and len(term) > 4:
        return term[:-1]

    return term


def _terms(text: str) -> list[str]:
    # Turn a text query into useful searchable terms.
    #
    # Steps:
    # 1. Lowercase the text.
    # 2. Extract word-like chunks with WORD_RE.
    # 3. Remove stopwords.
    # 4. Normalize the remaining words.
    return [
        _normalize_term(w)
        for w in WORD_RE.findall(text.lower())
        if w not in STOPWORDS
    ]


def search_products(
    products: list[dict[str, Any]],
    query: str,
    max_results: int = 3,
) -> list[dict[str, Any]]:
    """Simple transparent keyword search for the tiny static catalog."""

    # Convert the user's query into cleaned-up search terms.
    query_terms = _terms(query)

    # If the query has no meaningful terms, return the first few products.
    if not query_terms:
        return products[:max_results]

    # Store pairs of (score, product).
    scored: list[tuple[int, dict[str, Any]]] = []

    # Score each product against the query.
    for product in products:
        # Lowercase each searchable field so matching is case-insensitive.
        name = product["ProductName"].lower()
        description = product["Description"].lower()
        tags = " ".join(product.get("Tags", [])).lower()
        sku = product["SKU"].lower()

        score = 0

        # Add points depending on where the search term appears.
        # SKU and product name matches matter the most.
        # Tags matter somewhat.
        # Description matches matter the least.
        for term in query_terms:
            if term in sku:
                score += 10
            if term in name:
                score += 8
            if term in tags:
                score += 3
            if term in description:
                score += 1

        # Only keep products that matched at least one term.
        if score > 0:
            scored.append((score, product))

    # Sort by:
    # 1. Higher score first
    # 2. Product name alphabetically as a tie-breaker
    scored.sort(key=lambda item: (-item[0], item[1]["ProductName"]))

    # Return only the product dictionaries, not the scores.
    return [product for _, product in scored[:max_results]]


def is_early_risers_request(message: str) -> bool:
    # Check whether the user is asking about the Early Risers discount.
    lower = message.lower()
    return "early risers" in lower or "early riser" in lower


def is_early_risers_window(now: datetime | None = None) -> bool:
    # If no datetime is passed in, use the current time in Los Angeles.
    now = now or datetime.now(ZoneInfo("America/Los_Angeles"))

    # If the datetime has no timezone, assume it is Los Angeles time.
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("America/Los_Angeles"))

    # Convert the datetime to Los Angeles time.
    now_pt = now.astimezone(ZoneInfo("America/Los_Angeles"))

    # Early Risers discount is available from 8:00 AM through 9:59 AM PT.
    return 8 <= now_pt.hour < 10


def generate_discount_code() -> str:
    # Generate a random discount code.
    # secrets.token_hex(4) creates 8 random hexadecimal characters.
    # Example: "EARLY-A1B2C3D4"
    return f"EARLY-{secrets.token_hex(4).upper()}"
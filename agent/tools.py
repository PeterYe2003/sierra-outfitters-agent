from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
ORDER_RE = re.compile(r"#?\s*[Ww]\s*-?\s*\d+", re.IGNORECASE)
WORD_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "for", "from", "i",
    "in", "is", "it", "me", "my", "of", "on", "or", "please", "something",
    "that", "the", "to", "what", "with", "you", "your", "need", "want", "looking",
    "recommend", "recommendation", "product", "gear", "item", "items",
}


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_order_number(order_number: str) -> str:
    num_match = re.search(r"\d+", order_number)
    if num_match:
        num_str = num_match.group(0).zfill(3)
        return f"#W{num_str}"
    
    cleaned = order_number.strip().upper()
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    return cleaned


def extract_email(message: str) -> str | None:
    match = EMAIL_RE.search(message)
    return match.group(0).lower() if match else None


def extract_order_number(message: str) -> str | None:
    match = ORDER_RE.search(message)
    if match:
        return normalize_order_number(match.group(0))
        
    context_match = re.search(r"order\s*(?:number|#)?\s*(\d+)", message, re.IGNORECASE)
    if context_match:
        return normalize_order_number(context_match.group(1))
        
    return None


def lookup_order(
    orders: list[dict[str, Any]],
    email: str,
    order_number: str,
) -> dict[str, Any] | None:
    normalized_email = email.strip().lower()
    normalized_order = normalize_order_number(order_number)

    for order in orders:
        if (
            order.get("Email", "").lower() == normalized_email
            and normalize_order_number(order.get("OrderNumber", "")) == normalized_order
        ):
            result = dict(order)
            tracking_number = result.get("TrackingNumber")
            result["TrackingLink"] = (
                f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
                if tracking_number
                else None
            )
            return result
    return None


def products_by_sku(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {p["SKU"]: p for p in products}


def enrich_order_products(
    order: dict[str, Any], products: list[dict[str, Any]]
) -> dict[str, Any]:
    sku_to_product = products_by_sku(products)
    enriched = dict(order)
    enriched["ProductDetails"] = [
        sku_to_product.get(sku, {"SKU": sku, "ProductName": "Unknown product"})
        for sku in order.get("ProductsOrdered", [])
    ]
    return enriched


def _normalize_term(term: str) -> str:
    # Tiny normalization for common catalog queries without adding dependencies.
    if term == "snowy":
        return "snow"
    if term.endswith("ing") and len(term) > 5:
        return term[:-3]
    if term.endswith("s") and len(term) > 4:
        return term[:-1]
    return term


def _terms(text: str) -> list[str]:
    return [_normalize_term(w) for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS]


def search_products(
    products: list[dict[str, Any]], query: str, max_results: int = 3
) -> list[dict[str, Any]]:
    """Simple transparent keyword search for the tiny static catalog."""
    query_terms = _terms(query)
    if not query_terms:
        return products[:max_results]

    scored: list[tuple[int, dict[str, Any]]] = []
    for product in products:
        name = product["ProductName"].lower()
        description = product["Description"].lower()
        tags = " ".join(product.get("Tags", [])).lower()
        sku = product["SKU"].lower()

        score = 0
        for term in query_terms:
            if term in sku:
                score += 5
            if term in name:
                score += 4
            if term in tags:
                score += 3
            if term in description:
                score += 1

        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], item[1]["ProductName"]))
    return [product for _, product in scored[:max_results]]


def is_early_risers_request(message: str) -> bool:
    lower = message.lower()
    return "early risers" in lower or "early riser" in lower


def is_early_risers_window(now: datetime | None = None) -> bool:
    now = now or datetime.now(ZoneInfo("America/Los_Angeles"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    now_pt = now.astimezone(ZoneInfo("America/Los_Angeles"))
    return 8 <= now_pt.hour < 10


def generate_discount_code() -> str:
    return f"EARLY-{secrets.token_hex(4).upper()}"

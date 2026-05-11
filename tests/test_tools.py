from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agent.router import handle_message
from agent.models import ConversationState
from agent.tools import (
    extract_order_number,
    is_early_risers_window,
    load_json,
    lookup_order,
    search_products,
)

ROOT = Path(__file__).resolve().parents[1]
ORDERS = load_json(ROOT / "data" / "CustomerOrders.json")
PRODUCTS = load_json(ROOT / "data" / "ProductCatalog.json")


def test_extract_order_number_normalizes_hash() -> None:
    assert extract_order_number("my order is W002") == "#W002"
    assert extract_order_number("my order is #w002") == "#W002"


def test_lookup_order_adds_tracking_link() -> None:
    order = lookup_order(ORDERS, "jane.smith@example.com", "W002")
    assert order is not None
    assert order["Status"] == "in-transit"
    assert order["TrackingLink"].endswith("TRK987654321")


def test_lookup_order_returns_none_for_wrong_email() -> None:
    assert lookup_order(ORDERS, "wrong@example.com", "W002") is None


def test_search_products_hiking_returns_backpack() -> None:
    matches = search_products(PRODUCTS, "I need hiking gear")
    assert matches
    assert matches[0]["SKU"] == "SOBP001"


def test_search_products_snow_returns_skis() -> None:
    matches = search_products(PRODUCTS, "snowy mountain trip")
    assert matches
    assert matches[0]["SKU"] == "SOTN002"


def test_early_risers_window() -> None:
    valid = datetime(2026, 1, 1, 8, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    invalid = datetime(2026, 1, 1, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    assert is_early_risers_window(valid)
    assert not is_early_risers_window(invalid)


def test_router_collects_missing_order_info_across_turns() -> None:
    state = ConversationState()
    first = handle_message("Where is my order?", state, ORDERS, PRODUCTS)
    assert first.facts["status"] == "missing_information"

    second = handle_message("jane.smith@example.com W002", state, ORDERS, PRODUCTS)
    assert second.facts["status"] == "found"
    assert second.facts["order"]["TrackingNumber"] == "TRK987654321"


def test_router_only_generates_promo_when_explicit_and_valid() -> None:
    state = ConversationState()
    now = datetime(2026, 1, 1, 8, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    decision = handle_message("Can I get the Early Risers Promotion?", state, ORDERS, PRODUCTS, now=now)
    assert decision.facts["status"] == "eligible"
    assert decision.facts["code"].startswith("EARLY-")


def test_router_does_not_generate_for_vague_discount() -> None:
    state = ConversationState()
    now = datetime(2026, 1, 1, 8, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    decision = handle_message("Do you have any discounts?", state, ORDERS, PRODUCTS, now=now)
    assert decision.facts["status"] == "no_explicit_early_risers_request"

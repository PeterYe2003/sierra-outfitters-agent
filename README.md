# Sierra Outfitters Agent

A small terminal-based customer support agent for the Sierra Outfitters take-home assignment.

The implementation keeps the agent simple:

- The LLM handles customer-facing wording and brand tone.
- Deterministic Python functions handle order lookup, USPS tracking links, product recommendations, and Early Risers eligibility.
- Static JSON files from the appendices are loaded locally.

## Features

1. **Order Status and Tracking**
   - Asks for email and order number when missing.
   - Looks up matching orders from `data/CustomerOrders.json`.
   - Supports order numbers with or without the `#`, such as `#W002` or `W002`.
   - Adds a USPS tracking link when a tracking number exists.

2. **Product Recommendations**
   - Searches `data/ProductCatalog.json` using a transparent keyword scorer over product name, SKU, description, and tags.
   - Returns product name, SKU, inventory, and a short recommendation.

3. **Early Risers Promotion**
   - Generates a unique 10% discount code only when the customer explicitly asks for the Early Risers Promotion.
   - Checks the 8:00 AM-10:00 AM Pacific Time window using `zoneinfo`.
   - Reuses the same code for the same email during a session.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your OpenAI API key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

Then export it before running:

```bash
source .env
python main.py
```

You can also run without an API key. In that case, the app uses deterministic fallback responses, which is useful for local testing.

## Usage

```bash
python main.py
```

Optional model override:

```bash
python main.py --model gpt-4o
```

## Demo Prompts

Try these during the walkthrough:

```text
Where is my order?
```

Then:

```text
jane.smith@example.com W002
```

Product recommendation examples:

```text
Can you recommend something for a snowy mountain trip?
I need a snack or drink for a long hike.
What do you sell for stealthy wilderness exploration?
```

Promotion examples:

```text
Can I get the Early Risers Promotion?
Do you have any discounts?
```
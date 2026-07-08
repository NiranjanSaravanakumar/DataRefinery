"""
DataRefinery — Pipeline Rules Configuration
=============================================
Centralised configuration for all validation rules, thresholds,
and data mapping dictionaries used by the ETL pipeline.

Keeping these in a single module makes it easy to adjust validation
behaviour without touching pipeline logic.
"""

from __future__ import annotations

from decimal import Decimal

# ── Required CSV columns ──────────────────────────────────────────────────────

REQUIRED_FIELDS: list[str] = [
    "order_id",
    "customer_id",
    "order_date",
    "ship_date",
    "region",
    "category",
    "quantity",
    "unit_price",
    "status",
]

# ── Status normalisation map ──────────────────────────────────────────────────
# Keys are lowercased raw values; values are the canonical display names.

VALID_STATUSES: dict[str, str] = {
    "delivered": "Delivered",
    "shipped": "Shipped",
    "processing": "Processing",
    "cancelled": "Cancelled",
    "returned": "Returned",
}

# ── Region alias map ──────────────────────────────────────────────────────────
# Keys are lowercased and stripped raw values; values are canonical region names.

REGION_ALIASES: dict[str, str] = {
    "northeast": "Northeast",
    "north east": "Northeast",
    "ne": "Northeast",
    "southeast": "Southeast",
    "south east": "Southeast",
    "se": "Southeast",
    "midwest": "Midwest",
    "mid west": "Midwest",
    "mw": "Midwest",
    "west": "West",
    "w": "West",
    "southwest": "Southwest",
    "south west": "Southwest",
    "sw": "Southwest",
    "northwest": "Northwest",
    "north west": "Northwest",
    "nw": "Northwest",
}

# ── Financial thresholds ──────────────────────────────────────────────────────

# Orders with revenue >= this amount, or with status "Processing", are flagged
# as priority lane.
PRIORITY_REVENUE_THRESHOLD: Decimal = Decimal("500")

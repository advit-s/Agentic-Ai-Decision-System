"""Synthetic demo dataset definitions and seed generator for v0.3.1.

Generates safe, fake business CSVs under ``company_data/<category>/`` so
local profiling and future pattern-detection have representative data without
exposing real (private) company information.
"""

from __future__ import annotations

import csv
from hashlib import sha1
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Category -> filename mapping (must match ALL_CATEGORIES minus "unknown")
# ---------------------------------------------------------------------------

DEMO_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("financial", "demo_financials.csv"),
    ("customers", "demo_customers.csv"),
    ("sales", "demo_sales.csv"),
    ("marketing", "demo_marketing.csv"),
    ("feedback", "demo_feedback.csv"),
    ("products", "demo_products.csv"),
    ("competitors", "demo_competitors.csv"),
    ("operations", "demo_operations.csv"),
    ("analytics", "demo_analytics.csv"),
    ("strategic", "demo_strategy.csv"),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def _read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _stable_mod(modulo: int, *parts: Any) -> int:
    """Return a deterministic pseudo-random integer for demo data."""

    digest = sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


# ---------------------------------------------------------------------------
# Dataset generators – return (headers, rows)
# ---------------------------------------------------------------------------


def _demo_financials() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["month", "product", "revenue", "expenses", "profit_margin"]
    rows: list[dict[str, Any]] = []
    products = ["Nimbus", "Orion", "Titan", "Vertex"]
    for i in range(12):
        month = f"2025-{i + 1:02d}"
        for product in products:
            revenue = max(8000, 20000 + (i * 420) + _stable_mod(8000, product))
            expenses = round(revenue * (0.55 + _stable_mod(30, i, product) / 100))
            margin = round((revenue - expenses) / revenue, 4)
            rows.append(
                {
                    "month": month,
                    "product": product,
                    "revenue": revenue,
                    "expenses": expenses,
                    "profit_margin": margin,
                }
            )
    # Add a couple of tight-margin observations
    rows.append(
        {
            "month": "2025-01",
            "product": "Vertex",
            "revenue": 12000,
            "expenses": 11850,
            "profit_margin": 0.0125,
        }
    )
    rows.append(
        {
            "month": "2025-06",
            "product": "Orion",
            "revenue": 15000,
            "expenses": 14100,
            "profit_margin": 0.06,
        }
    )
    return headers, rows


def _demo_customers() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["customer_id", "city", "segment", "signup_month", "lifetime_value"]
    rows: list[dict[str, Any]] = []
    cities = [
        "New York",
        "Chicago",
        "Austin",
        "Denver",
        "Seattle",
        "Miami",
        "Boston",
        "Portland",
    ]
    segments = [
        "enterprise",
        "smb",
        "smb",
        "startup",
        "enterprise",
        "enterprise",
        "smb",
        "startup",
        "enterprise",
        "smb",
    ]
    for idx in range(24):
        city = cities[idx % len(cities)]
        segment = segments[idx % len(segments)]
        signup = f"2025-{(idx % 12) + 1:02d}"
        base = 4000 if segment == "smb" else 15000 if segment == "enterprise" else 8000
        ltv = base + _stable_mod(7000, idx)
        rows.append(
            {
                "customer_id": f"CUST-{idx + 1:04d}",
                "city": city,
                "segment": segment,
                "signup_month": signup,
                "lifetime_value": ltv,
            }
        )
    return headers, rows


def _demo_sales() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["month", "product", "region", "sales_amount", "lead_source"]
    rows: list[dict[str, Any]] = []
    sources = [
        "Organic",
        "Paid",
        "Referral",
        "Social",
        "Email",
        "Organic",
        "Organic",
        "Paid",
    ]
    products = ["Nimbus", "Orion", "Titan", "Vertex"]
    regions = ["North", "South", "East", "West", "Midwest"]
    for idx in range(24):
        month = f"2025-{((idx % 12) + 1):02d}"
        product = products[idx % len(products)]
        region = regions[idx % len(regions)]
        source = sources[idx % len(sources)]
        amount = 1500 + _stable_mod(14000, idx, product)
        rows.append(
            {
                "month": month,
                "product": product,
                "region": region,
                "sales_amount": amount,
                "lead_source": source,
            }
        )
    return headers, rows


def _demo_marketing() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["month", "channel", "spend", "clicks", "conversions", "revenue"]
    rows: list[dict[str, Any]] = []
    channels = [
        {"name": "Google Ads", "spend_factor": 4.5, "cvr": 0.08},
        {"name": "LinkedIn", "spend_factor": 2.8, "cvr": 0.05},
        {"name": "Email", "spend_factor": 0.6, "cvr": 0.14},
        {"name": "TikTok", "spend_factor": 1.2, "cvr": 0.02},  # poor ROI
    ]
    for i in range(12):
        month = f"2025-{i + 1:02d}"
        for ch in channels:
            spend = round(2000 * ch["spend_factor"], 2)
            clicks = int(spend * 8 + _stable_mod(1500, i, ch["name"]))
            conversions = max(1, int(clicks * ch["cvr"]))
            revenue = round(conversions * (120 + _stable_mod(100, ch["name"])), 2)
            rows.append(
                {
                    "month": month,
                    "channel": ch["name"],
                    "spend": spend,
                    "clicks": clicks,
                    "conversions": conversions,
                    "revenue": revenue,
                }
            )
    return headers, rows


def _demo_feedback() -> tuple[list[str], list[dict[str, Any]]]:
    headers = [
        "ticket_id",
        "customer_segment",
        "issue_type",
        "sentiment",
        "refund_requested",
    ]
    rows: list[dict[str, Any]] = []
    issue_types = [
        "Login failure",
        "Billing discrepancy",
        "Login failure",
        "Feature request",
        "Billing discrepancy",
        "Slow performance",
        "Login failure",
        "Account locked",
        "Billing discrepancy",
        "Feature request",
        "Login failure",
        "Slow performance",
    ]
    sentiments = [
        "negative",
        "neutral",
        "negative",
        "positive",
        "negative",
        "negative",
        "negative",
        "negative",
    ]
    segments = ["enterprise", "smb", "startup", "smb", "enterprise"]
    refund = [
        "true",
        "false",
        "true",
        "false",
        "false",
        "true",
        "false",
        "false",
        "true",
        "false",
        "true",
        "false",
    ]
    for idx, issue in enumerate(issue_types):
        rows.append(
            {
                "ticket_id": f"TK-{idx + 1:04d}",
                "customer_segment": segments[idx % len(segments)],
                "issue_type": issue,
                "sentiment": sentiments[idx % len(sentiments)],
                "refund_requested": refund[idx % len(refund)],
            }
        )
    return headers, rows


def _demo_products() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["product", "category", "units_sold", "gross_margin", "return_rate"]
    rows: list[dict[str, Any]] = [
        {
            "product": "Nimbus Pro",
            "category": "SaaS",
            "units_sold": 3420,
            "gross_margin": 0.72,
            "return_rate": 0.02,
        },
        {
            "product": "Orion Basic",
            "category": "SaaS",
            "units_sold": 1890,
            "gross_margin": 0.68,
            "return_rate": 0.04,
        },
        {
            "product": "Titan Enterprise",
            "category": "SaaS",
            "units_sold": 920,
            "gross_margin": 0.81,
            "return_rate": 0.01,
        },
        {
            "product": "Vertex Lite",
            "category": "SaaS",
            "units_sold": 4100,
            "gross_margin": 0.22,  # low margin
            "return_rate": 0.18,  # high return rate
        },
        {
            "product": "Nimbus AddOn Pack",
            "category": "Add-on",
            "units_sold": 1500,
            "gross_margin": 0.55,
            "return_rate": 0.03,
        },
    ]
    return headers, rows


def _demo_competitors() -> tuple[list[str], list[dict[str, Any]]]:
    headers = [
        "competitor",
        "product_category",
        "competitor_price",
        "our_price",
        "review_score",
    ]
    rows: list[dict[str, Any]] = [
        {
            "competitor": "Acme Corp",
            "product_category": "SaaS",
            "competitor_price": 899,
            "our_price": 799,
            "review_score": 3.4,
        },
        {
            "competitor": "BetaSoft",
            "product_category": "SaaS",
            "competitor_price": 749,  # lower price
            "our_price": 799,
            "review_score": 4.6,  # better reviews
        },
        {
            "competitor": "GammaCloud",
            "product_category": "SaaS",
            "competitor_price": 1299,
            "our_price": 999,
            "review_score": 3.9,
        },
        {
            "competitor": "DeltaWorks",
            "product_category": "Add-on",
            "competitor_price": 199,
            "our_price": 149,
            "review_score": 3.1,
        },
    ]
    return headers, rows


def _demo_operations() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["process", "average_delay_days", "cost", "bottleneck"]
    rows: list[dict[str, Any]] = [
        {
            "process": "Invoice processing",
            "average_delay_days": 2,
            "cost": 1500,
            "bottleneck": "false",
        },
        {
            "process": "Payment reconciliation",
            "average_delay_days": 8,
            "cost": 4200,
            "bottleneck": "true",
        },
        {
            "process": "Vendor onboarding",
            "average_delay_days": 3,
            "cost": 2100,
            "bottleneck": "false",
        },
        {
            "process": "Expense approval",
            "average_delay_days": 5,
            "cost": 1800,
            "bottleneck": "false",
        },
        {
            "process": "Report generation",
            "average_delay_days": 1,
            "cost": 800,
            "bottleneck": "false",
        },
    ]
    return headers, rows


def _demo_analytics() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["page", "traffic_source", "sessions", "bounce_rate", "conversion_rate"]
    rows: list[dict[str, Any]] = [
        {
            "page": "/pricing",
            "traffic_source": "Organic",
            "sessions": 8500,
            "bounce_rate": 0.45,
            "conversion_rate": 0.09,
        },
        {
            "page": "/blog",
            "traffic_source": "Organic",
            "sessions": 22000,
            "bounce_rate": 0.78,
            "conversion_rate": 0.01,
        },
        {
            "page": "/features",
            "traffic_source": "Paid",
            "sessions": 4100,
            "bounce_rate": 0.38,
            "conversion_rate": 0.12,
        },
        {
            "page": "/docs",
            "traffic_source": "Direct",
            "sessions": 3200,
            "bounce_rate": 0.33,
            "conversion_rate": 0.06,
        },
        {
            "page": "/support",
            "traffic_source": "Email",
            "sessions": 1800,
            "bounce_rate": 0.55,
            "conversion_rate": 0.03,
        },
    ]
    return headers, rows


def _demo_strategy() -> tuple[list[str], list[dict[str, Any]]]:
    headers = ["goal", "target_market", "priority", "constraint", "owner"]
    rows: list[dict[str, Any]] = [
        {
            "goal": "Double ARR in 18 months",
            "target_market": "Mid-market enterprise",
            "priority": "P0",
            "constraint": "Headcount freeze",
            "owner": "VP Revenue",
        },
        {
            "goal": "Expand EMEA presence",
            "target_market": "Western Europe",
            "priority": "P1",
            "constraint": "GDPR compliance",
            "owner": "VP International",
        },
        {
            "goal": "Reduce churn below 3%",
            "target_market": "All segments",
            "priority": "P0",
            "constraint": "Product roadmap locked",
            "owner": "VP Customer Success",
        },
        {
            "goal": "Launch self-serve tier",
            "target_market": "Startup",
            "priority": "P2",
            "constraint": "No additional dev headcount",
            "owner": "VP Product",
        },
        {
            "goal": "Achieve SOC 2 certification",
            "target_market": "Enterprise",
            "priority": "P1",
            "constraint": "Security budget cap",
            "owner": "CISO",
        },
    ]
    return headers, rows


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_DATASET_BUILDERS = {
    ("financial", "demo_financials.csv"): _demo_financials,
    ("customers", "demo_customers.csv"): _demo_customers,
    ("sales", "demo_sales.csv"): _demo_sales,
    ("marketing", "demo_marketing.csv"): _demo_marketing,
    ("feedback", "demo_feedback.csv"): _demo_feedback,
    ("products", "demo_products.csv"): _demo_products,
    ("competitors", "demo_competitors.csv"): _demo_competitors,
    ("operations", "demo_operations.csv"): _demo_operations,
    ("analytics", "demo_analytics.csv"): _demo_analytics,
    ("strategic", "demo_strategy.csv"): _demo_strategy,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def seed_demo_data(
    data_root: Path | str,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Create or update synthetic demo CSV files under *data_root*.

    Parameters
    ----------
    data_root:
        Root directory (usually ``company_data/``).
    force:
        When *False* (default) existing demo files are skipped.
        When *True* they are overwritten.

    Returns a summary dict with keys:
    ``created``, ``skipped``, ``overwritten``.
    """
    root = Path(data_root)
    summary: dict[str, int] = {"created": 0, "skipped": 0, "overwritten": 0}

    for category, filename in DEMO_CATEGORIES:
        key = (category, filename)
        builder = _DATASET_BUILDERS.get(key)
        if builder is None:
            raise KeyError(f"No generator registered for {key}")
        headers, rows = builder()
        target = root / category / filename
        if target.exists():
            if force:
                _write_csv(target, rows, headers)
                summary["overwritten"] += 1
            else:
                summary["skipped"] += 1
        else:
            _write_csv(target, rows, headers)
            summary["created"] += 1

    return summary

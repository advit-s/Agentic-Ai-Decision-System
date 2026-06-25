"""Deterministic pattern and vulnerability detectors for v0.4.

Each detector inspects saved data profiles, the local knowledge graph, and
(only when profile data is insufficient) raw CSV files under ``company_data/``.
All logic is rule-based and offline — no LLM is called.

Thresholds are intentionally conservative to minimise false positives.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from decision_system.data_catalog.loader import load_csv
from decision_system.data_catalog.models import DataProfileStore
from decision_system.graphing.models import KnowledgeGraph
from decision_system.insights.models import (
    Insight,
    InsightSeverity,
    InsightStore,
)

if TYPE_CHECKING:
    pass  # paths use run-time Path import above

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MISSING_DATA_MEDIUM_PCT = 0.20  # > 20 % missing → medium
MISSING_DATA_HIGH_PCT = 0.50  # > 50 % missing → high

SALES_CHANNEL_MEDIUM_SHARE = 0.60  # > 60 % one channel → medium
SALES_CHANNEL_HIGH_SHARE = 0.80  # > 80 % → high

CUSTOMER_CONCENTRATION_MEDIUM = 0.50  # > 50 % one segment/city → medium
CUSTOMER_CONCENTRATION_HIGH = 0.80  # > 80 % → high

EXPENSE_REVENUE_RISK_RATIO = 0.90  # expenses >= 90 % of revenue
MARKETING_ROAS_RISK_THRESHOLD = 1.0  # ROAS < 1.0 → risk

PROFIT_MARGIN_LOW = 0.10  # average margin below 10 % → profit_margin_risk
PROFIT_MARGIN_CRITICAL = 0.05  # below 5 % → high

PRODUCT_LOW_MARGIN = 0.15  # gross margin below 15 %
PRODUCT_HIGH_RETURN = 0.10  # return rate above 10 %

COMPETITOR_LOWER_PRICE_BETTER_REVIEW = 1.0  # competitor price lower AND review higher

OPS_DELAY_THRESHOLD = 5.0  # average delay >= 5 days
OPS_BOTTLENECK_THRESHOLD = 3.0  # average delay >= 3 days when bottleneck=true

ANALYTICS_LOW_CONVERSION = 0.03  # conversion rate below 3 %
ANALYTICS_HIGH_BOUNCE = 0.60  # bounce rate above 60 %
ANALYTICS_LOW_CONV_WITH_HIGH_SESSIONS = 1000  # sessions above this AND conversion low

FB_NEGATIVE_THRESHOLD = 0.40  # > 40 % negative sentiment → risk
FB_REFUND_THRESHOLD = 0.25  # > 25 % refund requested → risk
FB_ISSUE_REPEAT_SHARE = 0.35  # one issue type > 35 % → risk

STRATEGIC_HIGH_PRIORITY_PREFIXES = ("P0", "P1")

DATA_QUALITY_MEDIUM_WARNINGS = 3
DATA_QUALITY_HIGH_WARNINGS = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_id(prefix: str, *parts: str) -> str:
    """Return a stable, readable insight id."""
    seed = "|".join(str(p) for p in parts)
    return f"{prefix}:{seed}"


def _safe_float(value: str) -> float | None:
    try:
        return float(value.strip().replace(",", "").replace("$", "").replace("%", ""))
    except (ValueError, TypeError):
        return None


def _find_column(profile, names: list[str]):
    """Return a ColumnProfile whose name matches any of *names* (case-insensitive)."""
    lower_names = [n.lower() for n in names]
    for col in profile.columns:
        if col.name.lower() in lower_names:
            return col
    return None


def _is_boolish(value: str) -> bool:
    return value.strip().lower() in ("true", "false", "yes", "no", "1", "0")


def _safe_bool(value: str) -> bool | None:
    v = value.strip().lower()
    if v in ("true", "yes", "1"):
        return True
    if v in ("false", "no", "0"):
        return False
    return None


def _load_csv_for(profile, csv_root: Path):
    """Load a CSV file corresponding to *profile* from the data catalog."""
    path = csv_root / profile.category / profile.filename
    if not path.exists():
        return None
    try:
        return load_csv(path, profile.category)
    except Exception:  # noqa: BLE001
        return None


def _affected_rows(loaded, col_name: str, threshold_fn) -> list[dict]:
    """Return rows where *col_name* passes *threshold_fn* (callable: value → bool)."""
    result = []
    for row in loaded.rows:
        val = _safe_float(row.get(col_name, ""))
        if val is not None and threshold_fn(val):
            result.append(row)
    return result


# ---------------------------------------------------------------------------
# Detector registry
# ---------------------------------------------------------------------------


def run_detectors(
    profiles: DataProfileStore | None = None,
    graph: KnowledgeGraph | None = None,
    csv_root: Path | str = "company_data",
) -> InsightStore:
    """Run all detectors and return the aggregated insight store."""

    profiles = profiles or DataProfileStore()
    graph = graph or KnowledgeGraph()
    root = Path(csv_root)
    store = InsightStore()

    # --- Group profiles by category for quick lookup ------------------------
    by_category: dict[str, list] = defaultdict(list)
    for p in profiles.profiles:
        by_category[p.category].append(p)

    # A. Profile-based -------------------------------------------------------
    for profile in profiles.profiles:
        _detect_missing_data(store, profile)
        _detect_data_quality(store, profile)

    sales_profiles = by_category.get("sales", [])
    if sales_profiles:
        _detect_sales_channel_concentration(store, sales_profiles, root)

    customer_profiles = by_category.get("customers", [])
    if customer_profiles:
        _detect_customer_concentration(store, customer_profiles, root)

    # B. Business CSV detectors ----------------------------------------------
    financial_profiles = by_category.get("financial", [])
    if financial_profiles:
        _detect_revenue_risk(store, financial_profiles, root)

    marketing_profiles = by_category.get("marketing", [])
    if marketing_profiles:
        _detect_marketing_roi(store, marketing_profiles, root)

    feedback_profiles = by_category.get("feedback", [])
    if feedback_profiles:
        _detect_feedback_risk(store, feedback_profiles, root)

    product_profiles = by_category.get("products", [])
    if product_profiles:
        _detect_product_risk(store, product_profiles, root)

    competitor_profiles = by_category.get("competitors", [])
    if competitor_profiles:
        _detect_competitor_risk(store, competitor_profiles, root)

    ops_profiles = by_category.get("operations", [])
    if ops_profiles:
        _detect_operations_bottleneck(store, ops_profiles, root)

    analytics_profiles = by_category.get("analytics", [])
    if analytics_profiles:
        _detect_analytics_conversion(store, analytics_profiles, root)

    strategic_profiles = by_category.get("strategic", [])
    if strategic_profiles:
        _detect_strategic_gap(store, strategic_profiles, root)

    # C. Graph-based --------------------------------------------------------
    _detect_dependency_risk(store, graph)
    _detect_contradiction(store, graph)
    _detect_ownership_gap(store, graph)

    return store


# ---------------------------------------------------------------------------
# A. Profile-based detectors
# ---------------------------------------------------------------------------


def _detect_missing_data(store: InsightStore, profile) -> None:
    for col in profile.columns:
        if col.missing_pct <= MISSING_DATA_MEDIUM_PCT:
            continue
        sev = "high" if col.missing_pct > MISSING_DATA_HIGH_PCT else "medium"
        insight = Insight(
            insight_id=_make_id("missing_data", profile.dataset_id, col.name),
            title=f"Missing data: {col.name} in {profile.filename}",
            description=(
                f"Column '{col.name}' in dataset '{profile.filename}' "
                f"is {col.missing_pct:.0%} missing ({col.missing_count} of {profile.row_count} rows)."
            ),
            category="missing_data",
            severity=sev,
            confidence="high",
            source_type="profile",
            source_ids=[profile.dataset_id],
            evidence_summary=f"{col.missing_count}/{profile.row_count} rows missing for column '{col.name}'",
            recommended_action=(
                "Investigate whether missing values indicate a data capture "
                "issue and impute or drop the column before analysis."
            ),
            ontology_concepts=["missing_data", "risk"],
        )
        store.add(insight)


def _detect_data_quality(store: InsightStore, profile) -> None:
    if not profile.warnings:
        return
    warning_count = len(profile.warnings)
    if warning_count >= DATA_QUALITY_HIGH_WARNINGS:
        sev = "high"
    elif warning_count >= DATA_QUALITY_MEDIUM_WARNINGS:
        sev = "medium"
    else:
        sev = "low"
    insight = Insight(
        insight_id=_make_id("data_quality", profile.dataset_id),
        title=f"Data quality warnings in {profile.filename}",
        description=(
            f"Dataset '{profile.filename}' produced {warning_count} profiling "
            f"warning(s), including: {profile.warnings[0]}"
        ),
        category="data_quality",
        severity=sev,
        confidence="high",
        source_type="profile",
        source_ids=[profile.dataset_id],
        evidence_summary="; ".join(f"{i + 1}. {w}" for i, w in enumerate(profile.warnings[:5])),
        recommended_action="Review and resolve profiling warnings before using this dataset for decision-making.",
        ontology_concepts=["data_quality", "risk"],
    )
    store.add(insight)


def _detect_sales_channel_concentration(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        col = _find_column(
            profile,
            ["lead_source", "channel", "source", "sales_channel", "source_channel"],
        )
        if col is None or not col.top_values or profile.row_count == 0:
            continue
        top_name, top_count = col.top_values[0]
        share = top_count / profile.row_count
        if share <= SALES_CHANNEL_MEDIUM_SHARE:
            continue
        sev = "high" if share > SALES_CHANNEL_HIGH_SHARE else "medium"
        insight = Insight(
            insight_id=_make_id("sales_channel_risk", profile.dataset_id, top_name, sev),
            title=f"Sales channel concentration: {top_name} in {profile.filename}",
            description=(
                f"Channel '{top_name}' accounts for {share:.0%} "
                f"({top_count}/{profile.row_count}) of rows in '{profile.filename}'."
            ),
            category="sales_channel_risk",
            severity=sev,
            confidence="high",
            source_type="profile",
            source_ids=[profile.dataset_id],
            evidence_summary=(
                f"Top channel '{top_name}': {top_count} / {profile.row_count} rows ({share:.0%})"
            ),
            recommended_action=(
                "Diversify sales channels to reduce concentration risk. "
                "Invest in underperforming channels."
            ),
            ontology_concepts=[
                "lead_source",
                "marketing_channel",
                "sales_channel_risk",
            ],
        )
        store.add(insight)


def _detect_customer_concentration(store: InsightStore, profiles: list, csv_root) -> None:
    segment_names = ["segment", "city", "region", "country", "industry", "vertical"]
    for profile in profiles:
        col = _find_column(profile, segment_names)
        if col is None or not col.top_values or profile.row_count == 0:
            continue
        # Use a categorical top_values summary
        top_name, top_count = col.top_values[0]
        share = top_count / profile.row_count
        if share <= CUSTOMER_CONCENTRATION_MEDIUM:
            continue
        sev = "high" if share > CUSTOMER_CONCENTRATION_HIGH else "medium"
        insight = Insight(
            insight_id=_make_id("customer_concentration", profile.dataset_id, top_name, sev),
            title=f"Customer concentration: {top_name} dominates {profile.filename}",
            description=(
                f"Customer segment '{top_name}' accounts for {share:.0%} "
                f"({top_count}/{profile.row_count}) of rows in '{profile.filename}'."
            ),
            category="customer_concentration",
            severity=sev,
            confidence="high",
            source_type="profile",
            source_ids=[profile.dataset_id],
            evidence_summary=(
                f"Top segment '{top_name}': {top_count} / {profile.row_count} rows ({share:.0%})"
            ),
            recommended_action=(
                "Diversify customer base to reduce single-segment dependency risk."
            ),
            ontology_concepts=[
                "customer_segment",
                "city",
                "region",
                "customer_concentration",
            ],
        )
        store.add(insight)


# ---------------------------------------------------------------------------
# B. Business CSV detectors — require raw CSV loading beyond profile data
# ---------------------------------------------------------------------------


def _detect_revenue_risk(store: InsightStore, profiles: list, csv_root) -> None:
    """Detect revenue risk and low profit margin from financial datasets."""
    for profile in profiles:
        rev_col = _find_column(profile, ["revenue", "total_revenue", "gross_revenue"])
        exp_col = _find_column(profile, ["expenses", "total_expenses", "costs", "cost"])
        margin_col = _find_column(profile, ["profit_margin", "margin", "net_margin"])

        # --- profit margin check from profile numeric summary ----------------
        if margin_col and margin_col.numeric_summary:
            mean_margin = margin_col.numeric_summary.get("mean", 0.0)
            if mean_margin < PROFIT_MARGIN_CRITICAL:
                sev: InsightSeverity = "high"
            elif mean_margin < PROFIT_MARGIN_LOW:
                sev = "medium"
            else:
                sev = "low"
            insight = Insight(
                insight_id=_make_id("profit_margin_risk", profile.dataset_id),
                title=f"Low average profit margin in {profile.filename}",
                description=(
                    f"Average profit margin in '{profile.filename}' is "
                    f"{mean_margin:.1%}, below the {PROFIT_MARGIN_LOW:.0%} threshold."
                ),
                category="profit_margin_risk",
                severity=sev,
                confidence="high",
                source_type="profile",
                source_ids=[profile.dataset_id],
                evidence_summary=(
                    f"Mean profit_margin={mean_margin:.4f} across {profile.row_count} rows"
                ),
                recommended_action="Investigate drivers of declining margins - cost structure, pricing, or mix shift.",
                ontology_concepts=["profit_margin", "revenue", "expense"],
            )
            store.add(insight)

        # --- expense-to-revenue ratio from raw CSV --------------------------
        if rev_col and exp_col:
            loaded = _load_csv_for(profile, csv_root)
            if loaded is None:
                continue

            # Find rows where expenses >= threshold of revenue
            breach_rows = []
            total_ratio = 0.0
            ratio_count = 0
            affected_months: set[str] = set()

            month_col = _find_column(profile, ["month", "period", "date", "date_month"])
            _find_column(profile, ["product", "product_name"])

            for row in loaded.rows:
                rev = _safe_float(row.get(rev_col.name, ""))
                exp = _safe_float(row.get(exp_col.name, ""))
                if rev is None or exp is None or rev <= 0:
                    continue
                ratio = exp / rev
                total_ratio += ratio
                ratio_count += 1
                if ratio >= EXPENSE_REVENUE_RISK_RATIO:
                    breach_rows.append(row)
                    if month_col:
                        affected_months.add(row.get(month_col.name, ""))

            avg_ratio = total_ratio / ratio_count if ratio_count else 0.0

            if breach_rows or avg_ratio >= EXPENSE_REVENUE_RISK_RATIO:
                severity = "high" if avg_ratio >= 0.95 or len(breach_rows) > 1 else "medium"
                parts = []
                if breach_rows:
                    parts.append(
                        f"{len(breach_rows)} row(s) with expenses >= {EXPENSE_REVENUE_RISK_RATIO:.0%} of revenue"
                    )
                if avg_ratio >= 0.80:
                    parts.append(f"average expense/revenue ratio is {avg_ratio:.1%}")
                evidence = "; ".join(parts)
                if affected_months:
                    months_display = ", ".join(sorted(affected_months)[:5])
                    desc_suffix = f" Affected periods: {months_display}."
                else:
                    desc_suffix = ""
                insight = Insight(
                    insight_id=_make_id("revenue_risk", profile.dataset_id, "expense_ratio"),
                    title=f"Revenue risk: high expense ratio in {profile.filename}",
                    description=(
                        f"Expenses in '{profile.filename}' reach or exceed "
                        f"{EXPENSE_REVENUE_RISK_RATIO:.0%} of revenue.{desc_suffix}"
                    ),
                    category="revenue_risk",
                    severity=severity,
                    confidence="high",
                    source_type="csv",
                    source_ids=[profile.dataset_id],
                    evidence_summary=evidence,
                    recommended_action=(
                        "Review expense drivers. Consider cost reductions or "
                        "revenue uplift strategies for affected periods."
                    ),
                    ontology_concepts=["revenue", "expense", "time_period"],
                )
                store.add(insight)


def _detect_marketing_roi(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        spend_col = _find_column(profile, ["spend", "ad_spend", "marketing_spend", "cost"])
        rev_col = _find_column(profile, ["revenue", "marketing_revenue", "attributed_revenue"])
        conv_col = _find_column(profile, ["conversions", "converted", "leads"])

        loaded = _load_csv_for(profile, csv_root)
        if loaded is None:
            continue

        channel_col = _find_column(
            profile, ["channel", "campaign_channel", "source", "source_channel"]
        )

        # Aggregate by channel if available
        by_channel: dict[str, list[dict]] = defaultdict(list)
        for row in loaded.rows:
            ch = row.get(channel_col.name, "unknown") if channel_col else "unknown"
            by_channel[ch].append(row)

        for channel, rows in by_channel.items():
            total_spend = 0.0
            total_rev = 0.0
            total_conv = 0
            for row in rows:
                s = _safe_float(row.get(spend_col.name, "")) if spend_col else None
                r = _safe_float(row.get(rev_col.name, "")) if rev_col else None
                c = _safe_float(row.get(conv_col.name, "")) if conv_col else None
                if s is not None:
                    total_spend += s
                if r is not None:
                    total_rev += r
                if c is not None:
                    total_conv += int(c)

            roas = total_rev / total_spend if total_spend > 0 else None
            reasons: list[str] = []
            if roas is not None and roas < MARKETING_ROAS_RISK_THRESHOLD:
                reasons.append(f"ROAS={roas:.2f} (below {MARKETING_ROAS_RISK_THRESHOLD:.1f})")
            if total_spend > 0 and total_conv == 0:
                reasons.append("spend exists but conversions are zero")
            elif total_spend > 0 and total_spend > 5000 and total_conv == 0:
                reasons.append(f"high spend (${total_spend:,.0f}) with no conversions")

            if not reasons:
                continue

            sev = "high" if (roas is not None and roas < 0.5) else "medium"
            insight = Insight(
                insight_id=_make_id("marketing_roi_risk", profile.dataset_id, channel),
                title=f"Marketing ROI risk: {channel} in {profile.filename}",
                description=(
                    f"Channel '{channel}' shows marketing ROI concerns: {'; '.join(reasons)}."
                ),
                category="marketing_roi_risk",
                severity=sev,
                confidence="high",
                source_type="csv",
                source_ids=[profile.dataset_id],
                evidence_summary=f"Channel: {channel}; " + "; ".join(reasons),
                recommended_action=(
                    "Review campaign performance. Consider pausing underperforming "
                    "spend and reallocating budget to higher-ROAS channels."
                ),
                ontology_concepts=[
                    "marketing_spend",
                    "revenue",
                    "conversion_count",
                    "marketing_channel",
                    "traffic_source",
                ],
            )
            store.add(insight)


def _detect_feedback_risk(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        issue_col = _find_column(profile, ["issue_type", "issue", "ticket_type", "problem_type"])
        sentiment_col = _find_column(profile, ["sentiment", "tone"])
        refund_col = _find_column(profile, ["refund_requested", "refund", "requested_refund"])
        _find_column(profile, ["customer_segment", "segment", "customer_id"])

        total = loaded.row_count

        # Issue type concentration
        if issue_col:
            counter: Counter = Counter()
            for row in loaded.rows:
                val = row.get(issue_col.name, "").strip()
                if val:
                    counter[val] += 1
            if counter:
                top_issue, top_count = counter.most_common(1)[0]
                share = top_count / total
                if share > FB_ISSUE_REPEAT_SHARE:
                    sev = "high" if share > 0.50 else "medium"
                    insight = Insight(
                        insight_id=_make_id(
                            "feedback_risk", profile.dataset_id, "issue_type", top_issue
                        ),
                        title=f"Feedback concentration: {top_issue} in {profile.filename}",
                        description=(
                            f"Issue type '{top_issue}' represents {share:.0%} of "
                            f"feedback records in '{profile.filename}' ({top_count}/{total})."
                        ),
                        category="feedback_risk",
                        severity=sev,
                        confidence="high",
                        source_type="csv",
                        source_ids=[profile.dataset_id],
                        evidence_summary=f"'{top_issue}': {top_count}/{total} rows ({share:.0%})",
                        recommended_action="Investigate root cause of the dominant issue type and prioritise remediation.",
                        ontology_concepts=[
                            "complaint_issue",
                            "customer_segment",
                            "feedback_risk",
                        ],
                    )
                    store.add(insight)

        # Sentiment and refunds
        negative_count = 0
        refund_count = 0
        for row in loaded.rows:
            if sentiment_col and row.get(sentiment_col.name, "").strip().lower() == "negative":
                negative_count += 1
            if refund_col and _safe_bool(row.get(refund_col.name, "")) is True:
                refund_count += 1

        if total > 0 and (negative_count / total) > FB_NEGATIVE_THRESHOLD:
            insight = Insight(
                insight_id=_make_id("feedback_risk", profile.dataset_id, "negative_sentiment"),
                title=f"High negative sentiment in {profile.filename}",
                description=(
                    f"Negative sentiment appears in {negative_count}/{total} records "
                    f"({negative_count / total:.0%}) in '{profile.filename}'."
                ),
                category="feedback_risk",
                severity="medium",
                confidence="high",
                source_type="csv",
                source_ids=[profile.dataset_id],
                evidence_summary=f"Negative sentiment: {negative_count}/{total} rows ({negative_count / total:.0%})",
                recommended_action="Review negative feedback themes and prioritise top issues for product or support teams.",
                ontology_concepts=["sentiment", "complaint_issue", "feedback_risk"],
            )
            store.add(insight)

        if total > 0 and (refund_count / total) > FB_REFUND_THRESHOLD:
            insight = Insight(
                insight_id=_make_id("feedback_risk", profile.dataset_id, "refund_rate"),
                title=f"High refund request rate in {profile.filename}",
                description=(
                    f"Refund requests appear in {refund_count}/{total} records "
                    f"({refund_count / total:.0%}) in '{profile.filename}'."
                ),
                category="feedback_risk",
                severity="high",
                confidence="high",
                source_type="csv",
                source_ids=[profile.dataset_id],
                evidence_summary=f"Refund requests: {refund_count}/{total} rows ({refund_count / total:.0%})",
                recommended_action="Investigate refund drivers - billing accuracy, product quality, or expectation mismatch.",
                ontology_concepts=["refund_requested", "feedback_risk"],
            )
            store.add(insight)


def _detect_product_risk(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        margin_col = _find_column(profile, ["gross_margin", "margin"])
        return_col = _find_column(profile, ["return_rate", "returns", "return_ratio"])
        units_col = _find_column(profile, ["units_sold", "units", "quantity", "qty_sold"])
        name_col = _find_column(profile, ["product", "product_name", "item"])

        if not margin_col or not return_col:
            continue

        for row in loaded.rows:
            margin = _safe_float(row.get(margin_col.name, ""))
            ret_rate = _safe_float(row.get(return_col.name, ""))
            if margin is None or ret_rate is None:
                continue
            if margin < PRODUCT_LOW_MARGIN and ret_rate > PRODUCT_HIGH_RETURN:
                product_name = row.get(name_col.name, "unknown") if name_col else "unknown"
                units = _safe_float(row.get(units_col.name, "")) if units_col else None
                sev = "high" if margin < 0.05 else "medium"
                insight = Insight(
                    insight_id=_make_id("product_risk", profile.dataset_id, product_name),
                    title=f"Product risk: {product_name} in {profile.filename}",
                    description=(
                        f"Product '{product_name}' has margin={margin:.1%} and "
                        f"return rate={ret_rate:.1%} in '{profile.filename}'."
                    ),
                    category="product_risk",
                    severity=sev,
                    confidence="high",
                    source_type="csv",
                    source_ids=[profile.dataset_id],
                    evidence_summary=(
                        f"margin={margin:.1%}, return_rate={ret_rate:.1%}"
                        + (f", units_sold={int(units)}" if units is not None else "")
                    ),
                    recommended_action=(
                        f"Review pricing, cost structure, and return reasons for '{product_name}'."
                    ),
                    ontology_concepts=[
                        "product",
                        "profit_margin",
                        "return_rate",
                        "product_risk",
                    ],
                )
                store.add(insight)


def _detect_competitor_risk(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        comp_price_col = _find_column(profile, ["competitor_price"])
        our_price_col = _find_column(profile, ["our_price", "company_price", "list_price"])
        review_col = _find_column(profile, ["review_score", "rating", "review_rating"])
        comp_name_col = _find_column(profile, ["competitor"])
        cat_col = _find_column(profile, ["product_category", "category"])

        if not comp_price_col or not our_price_col or not review_col:
            continue

        for row in loaded.rows:
            comp_price = _safe_float(row.get(comp_price_col.name, ""))
            our_price = _safe_float(row.get(our_price_col.name, ""))
            comp_review = _safe_float(row.get(review_col.name, ""))
            if comp_price is None or our_price is None or comp_review is None:
                continue
            if comp_price < our_price - 1 and comp_review > 3.5:
                comp_name = row.get(comp_name_col.name, "unknown") if comp_name_col else "unknown"
                cat = row.get(cat_col.name, "unknown") if cat_col else "unknown"
                delta = our_price - comp_price
                insight = Insight(
                    insight_id=_make_id("competitor_risk", profile.dataset_id, comp_name, cat),
                    title=f"Competitor price/review gap: {comp_name} vs {cat}",
                    description=(
                        f"Competitor '{comp_name}' offers '{cat}' at "
                        f"${comp_price:,.0f} (${delta:,.0f} cheaper than our ${our_price:,.0f}) "
                        f"with review score {comp_review:.1f}."
                    ),
                    category="competitor_risk",
                    severity="medium",
                    confidence="high",
                    source_type="csv",
                    source_ids=[profile.dataset_id],
                    evidence_summary=(
                        f"Competitor '{comp_name}' price=${comp_price:,.0f}, "
                        f"our price=${our_price:,.0f} (${delta:,.0f} cheaper by competitor), "
                        f"review_score={comp_review:.1f}"
                    ),
                    recommended_action=(
                        "Evaluate whether to match competitor pricing or "
                        "differentiate on features and value."
                    ),
                    ontology_concepts=[
                        "competitor",
                        "competitor_price",
                        "our_price",
                        "review_score",
                        "product",
                    ],
                )
                store.add(insight)


def _detect_operations_bottleneck(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        delay_col = _find_column(
            profile, ["average_delay_days", "delay_days", "avg_delay", "delay"]
        )
        bottleneck_col = _find_column(profile, ["bottleneck", "is_bottleneck"])
        cost_col = _find_column(profile, ["cost", "monthly_cost", "avg_cost"])
        process_col = _find_column(profile, ["process", "operation", "process_name"])

        if not delay_col:
            continue

        for row in loaded.rows:
            delay = _safe_float(row.get(delay_col.name, ""))
            if delay is None:
                continue

            is_bottleneck = False
            if bottleneck_col:
                bv = row.get(bottleneck_col.name, "").strip().lower()
                is_bottleneck = bv in ("true", "yes", "1")

            if is_bottleneck and delay >= OPS_BOTTLENECK_THRESHOLD:
                sev = "high" if delay >= 8 else "medium"
            elif delay >= OPS_DELAY_THRESHOLD:
                sev = "medium"
            else:
                continue

            process = row.get(process_col.name, "unknown") if process_col else "unknown"
            cost = _safe_float(row.get(cost_col.name, "")) if cost_col else None
            cost_str = f"cost=${cost:,.0f}/mo" if cost is not None else ""

            insight = Insight(
                insight_id=_make_id("operations_bottleneck", profile.dataset_id, process),
                title=f"Operations bottleneck: {process} in {profile.filename}",
                description=(
                    f"Process '{process}' has an average delay of {delay:.0f} days "
                    f"in '{profile.filename}'."
                ),
                category="operations_bottleneck",
                severity=sev,
                confidence="high",
                source_type="csv",
                source_ids=[profile.dataset_id],
                evidence_summary=(
                    f"average_delay_days={delay:.1f}"
                    + (f", bottleneck={str(is_bottleneck).lower()}" if bottleneck_col else "")
                    + (f", {cost_str}" if cost is not None else "")
                ),
                recommended_action=(
                    "Analyse the process for automation or resource "
                    f"improvements to reduce the {delay:.0f}-day average delay."
                ),
                ontology_concepts=["process", "operational_delay", "bottleneck"],
            )
            store.add(insight)


def _detect_analytics_conversion(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        sessions_col = _find_column(profile, ["sessions", "page_sessions", "visits"])
        bounce_col = _find_column(profile, ["bounce_rate", "bounce_rate_pct"])
        conv_col = _find_column(profile, ["conversion_rate", "conversion_rate_pct", "conversions"])
        page_col = _find_column(profile, ["page", "page_path", "url", "landing_page"])
        source_col = _find_column(profile, ["traffic_source", "source", "channel"])

        if not conv_col:
            continue

        for row in loaded.rows:
            conv = _safe_float(row.get(conv_col.name, ""))
            if conv is None:
                continue
            reasons: list[str] = []

            # Low conversion with high sessions
            if sessions_col:
                sessions = _safe_float(row.get(sessions_col.name, ""))
                if (
                    sessions is not None
                    and sessions > ANALYTICS_LOW_CONV_WITH_HIGH_SESSIONS
                    and conv < ANALYTICS_LOW_CONVERSION
                ):
                    reasons.append(f"{int(sessions)} sessions with only {conv:.1%} conversion")

            # High bounce rate
            if bounce_col:
                bounce = _safe_float(row.get(bounce_col.name, ""))
                if bounce is not None and bounce > ANALYTICS_HIGH_BOUNCE:
                    reasons.append(f"bounce_rate={bounce:.0%}")

            if not reasons:
                continue

            page = row.get(page_col.name, "unknown") if page_col else "unknown"
            source = row.get(source_col.name, "unknown") if source_col else "unknown"
            sev = "high" if len(reasons) > 1 else "medium"

            insight = Insight(
                insight_id=_make_id("analytics_conversion_risk", profile.dataset_id, page, source),
                title=f"Conversion risk: {page} ({source}) in {profile.filename}",
                description=(
                    f"Page '{page}' with traffic source '{source}' shows "
                    f"conversion issues: {'; '.join(reasons)}."
                ),
                category="analytics_conversion_risk",
                severity=sev,
                confidence="high",
                source_type="csv",
                source_ids=[profile.dataset_id],
                evidence_summary=(f"page={page}, traffic_source={source}; " + "; ".join(reasons)),
                recommended_action=(
                    "Optimise landing page experience, reduce friction, "
                    "and review traffic-source quality."
                ),
                ontology_concepts=[
                    "page",
                    "session_count",
                    "bounce_rate",
                    "conversion_rate",
                    "traffic_source",
                ],
            )
            store.add(insight)


def _detect_strategic_gap(store: InsightStore, profiles: list, csv_root) -> None:
    for profile in profiles:
        loaded = _load_csv_for(profile, csv_root)
        if loaded is None or loaded.row_count == 0:
            continue

        goal_col = _find_column(profile, ["goal", "objective", "initiative", "strategy"])
        priority_col = _find_column(profile, ["priority", "priority_level", "tier"])
        constraint_col = _find_column(profile, ["constraint", "blocker", "risk_factor"])
        owner_col = _find_column(profile, ["owner", "owned_by", "lead", "responsible"])

        for row in loaded.rows:
            priority = row.get(priority_col.name, "").strip() if priority_col else ""
            is_high = any(priority.upper().startswith(p) for p in STRATEGIC_HIGH_PRIORITY_PREFIXES)

            if constraint_col and is_high:
                constraint = row.get(constraint_col.name, "").strip()
                if constraint:
                    goal = row.get(goal_col.name, "Unknown goal") if goal_col else "Unknown goal"
                    insight = Insight(
                        insight_id=_make_id(
                            "strategic_gap", profile.dataset_id, goal, "constraint"
                        ),
                        title=f"Strategic gap: {goal} faces constraints",
                        description=(f"High-priority goal '{goal}' is blocked by: '{constraint}'."),
                        category="strategic_gap",
                        severity="medium",
                        confidence="high",
                        source_type="csv",
                        source_ids=[profile.dataset_id],
                        evidence_summary=f"Goal: '{goal}'; Constraint: '{constraint}'; Priority: {priority}",
                        recommended_action=(
                            "Review whether the constraint can be resolved or "
                            "whether the timeline must be adjusted."
                        ),
                        ontology_concepts=["strategic_goal", "constraint"],
                    )
                    store.add(insight)

            if owner_col:
                owner = row.get(owner_col.name, "").strip()
                if not owner and goal_col:
                    goal = row.get(goal_col.name, "Unknown goal")
                    insight = Insight(
                        insight_id=_make_id(
                            "strategic_gap", profile.dataset_id, goal, "missing_owner"
                        ),
                        title=f"Ownership gap: {goal} has no owner",
                        description=(
                            f"Goal '{goal}' in '{profile.filename}' does not "
                            f"have an assigned owner."
                        ),
                        category="strategic_gap",
                        severity="low",
                        confidence="high",
                        source_type="csv",
                        source_ids=[profile.dataset_id],
                        evidence_summary=f"Goal: '{goal}' - owner field is empty",
                        recommended_action="Assign a clear owner to ensure accountability and progress tracking.",
                        ontology_concepts=["owner", "strategic_goal"],
                    )
                    store.add(insight)


# ---------------------------------------------------------------------------
# C. Graph-based detectors
# ---------------------------------------------------------------------------


def _outgoing_count(entity_id: str, relationships: list) -> int:
    return sum(1 for rel in relationships if rel.source_entity_id == entity_id)


def _detect_dependency_risk(store: InsightStore, graph: KnowledgeGraph) -> None:
    if not graph.relationships:
        return

    # Count incoming depends_on edges per entity
    incoming: dict[str, int] = defaultdict(int)
    entity_names: dict[str, str] = {}
    for e in graph.entities:
        entity_names[e.entity_id] = e.name

    for rel in graph.relationships:
        if rel.relation_type == "depends_on":
            incoming[rel.target_entity_id] += 1

    for entity_id, count in incoming.items():
        if count >= 2:
            name = entity_names.get(entity_id, entity_id)
            sev: InsightSeverity = "high" if count >= 4 else "medium"
            insight = Insight(
                insight_id=_make_id("dependency_risk", entity_id, str(count)),
                title=f"Dependency risk: {name} has {count} upstream dependencies",
                description=(
                    f"Entity '{name}' is the target of {count} 'depends_on' "
                    f"relationships, suggesting it is a single point of failure."
                ),
                category="dependency_risk",
                severity=sev,
                confidence="medium",
                source_type="graph",
                source_ids=[
                    r.relationship_id
                    for r in graph.relationships
                    if r.target_entity_id == entity_id
                ],
                evidence_summary=f"{count} 'depends_on' edges pointing to '{name}'",
                recommended_action=(
                    "Assess whether the dependency is a single point of "
                    "failure and plan redundancy or isolation strategies."
                ),
                ontology_concepts=["dependency"],
            )
            store.add(insight)


def _detect_contradiction(store: InsightStore, graph: KnowledgeGraph) -> None:
    entity_names: dict[str, str] = {}
    for e in graph.entities:
        entity_names[e.entity_id] = e.name

    for rel in graph.relationships:
        if rel.relation_type != "contradicts":
            continue
        source_name = entity_names.get(rel.source_entity_id, rel.source_entity_id)
        target_name = entity_names.get(rel.target_entity_id, rel.target_entity_id)
        insight = Insight(
            insight_id=_make_id("contradiction", rel.relationship_id),
            title=f"Contradiction: {source_name} vs {target_name}",
            description=(
                f"Graph relationship records a contradiction between "
                f"'{source_name}' and '{target_name}'."
            ),
            category="contradiction",
            severity="high",
            confidence="medium",
            source_type="graph",
            source_ids=[rel.relationship_id],
            evidence_summary=(f"contradicts: '{source_name}' <-> '{target_name}'"),
            recommended_action=(
                "Investigate these contradictory statements and determine "
                "which is correct based on current evidence."
            ),
            ontology_concepts=["contradiction"],
        )
        store.add(insight)


def _detect_ownership_gap(store: InsightStore, graph: KnowledgeGraph) -> None:
    """Flag system/project/technology entities without an owned_by relationship."""
    if not graph.entities or not graph.relationships:
        return

    # Build set of entity ids referenced as target of an owned_by edge
    owned_targets: set[str] = set()
    for rel in graph.relationships:
        if rel.relation_type == "owned_by":
            owned_targets.add(rel.target_entity_id)

    # Also check for owner-like relationships
    for rel in graph.relationships:
        if rel.relation_type in ("owned_by", "managed_by", "maintained_by"):
            owned_targets.add(rel.target_entity_id)

    target_types = {"system", "project", "technology"}
    for entity in graph.entities:
        if entity.entity_type not in target_types:
            continue
        if entity.entity_id in owned_targets:
            continue

        # Conservative: only flag if the entity has at least one relationship
        incoming_count = sum(
            1 for rel in graph.relationships if rel.target_entity_id == entity.entity_id
        )
        if incoming_count == 0 and _outgoing_count(entity.entity_id, graph.relationships) == 0:
            continue  # Isolated entity — skip to avoid noise

        insight = Insight(
            insight_id=_make_id("strategic_gap", "ownership", entity.entity_id),
            title=f"Ownership gap: {entity.name} ({entity.entity_type})",
            description=(
                f"Entity '{entity.name}' (type: {entity.entity_type}) does not "
                f"have an 'owned_by' relationship in the knowledge graph."
            ),
            category=(
                "operations_bottleneck" if entity.entity_type == "system" else "strategic_gap"
            ),
            severity="low",
            confidence="low",
            source_type="graph",
            source_ids=[entity.entity_id],
            evidence_summary=(
                f"No 'owned_by' or 'managed_by' relationship found for "
                f"entity '{entity.name}' ({entity.entity_type})"
            ),
            recommended_action=(
                "Assign an owner to this entity for accountability and incident response."
            ),
            ontology_concepts=["owner", "dependency"],
        )
        store.add(insight)

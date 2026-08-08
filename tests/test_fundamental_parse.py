"""Unit tests for Longbridge financial_report EPS/BPS parsing."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from catallax.providers.longbridge.fundamentals import (
    FUNDAMENTAL_SOURCE,
    extract_eps_bps_periods,
)


def test_extract_merges_eps_and_bps() -> None:
    period_end = date(2024, 6, 30)
    fp_end = str(int(datetime(2024, 6, 30, 12, 0, tzinfo=UTC).timestamp()))
    report = {
        "IS": {
            "indicators": [
                {
                    "currency": "USD",
                    "accounts": [
                        {
                            "field": "EPS",
                            "values": [
                                {
                                    "fp_end": fp_end,
                                    "period": "Q3 2024",
                                    "value": "1.40",
                                    "year": 2024,
                                    "yoy": "",
                                    "ratio": "",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        "BS": {
            "indicators": [
                {
                    "currency": "USD",
                    "accounts": [
                        {
                            "field": "BPS",
                            "values": [
                                {
                                    "fp_end": fp_end,
                                    "period": "Q3 2024",
                                    "value": "4.50",
                                    "year": 2024,
                                    "yoy": "",
                                    "ratio": "",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    }
    rows = extract_eps_bps_periods("AAPL.US", report)
    assert len(rows) == 1
    row = rows[0]
    assert row.provider_symbol == "AAPL.US"
    assert row.period_end == period_end
    assert row.period_label == "Q3 2024"
    assert row.eps == Decimal("1.40")
    assert row.bps == Decimal("4.50")
    assert row.available_date is None
    assert row.announcement_date is None
    assert row.source == FUNDAMENTAL_SOURCE


def test_skips_non_quarter_labels() -> None:
    report = {
        "IS": {
            "indicators": [
                {
                    "currency": "USD",
                    "accounts": [
                        {
                            "field": "EPS",
                            "values": [
                                {
                                    "fp_end": "1719792000",
                                    "period": "FY 2024",
                                    "value": "6.00",
                                    "year": 2024,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    }
    assert extract_eps_bps_periods("X.US", report) == []

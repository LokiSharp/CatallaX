"""Application-level enumerations stored as VARCHAR in PostgreSQL."""

from enum import StrEnum


class Market(StrEnum):
    """Top-level market region."""

    CN = "CN"
    US = "US"
    HK = "HK"


class InstrumentStatus(StrEnum):
    """Listing lifecycle status.

    Longbridge security_list / static_info do not provide this; only set when
    a real source is available (do not invent values).
    """

    ACTIVE = "active"
    DELISTED = "delisted"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class SyncEntity(StrEnum):
    """What a data sync job operates on."""

    INSTRUMENTS = "instruments"
    DAILY_PRICES = "daily_prices"
    VALUATION = "valuation"
    FUNDAMENTALS = "fundamentals"
    OTHER = "other"


class SyncStatus(StrEnum):
    """Lifecycle of a sync job row in data_sync_log."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

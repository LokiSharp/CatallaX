"""Application-level enumerations stored as VARCHAR in PostgreSQL."""

from enum import StrEnum


class Market(StrEnum):
    """Top-level market region."""

    CN = "CN"
    US = "US"
    HK = "HK"


class SyncEntity(StrEnum):
    """What a data sync job operates on."""

    INSTRUMENTS = "instruments"
    DAILY_PRICES = "daily_prices"
    FUNDAMENTALS = "fundamentals"
    VALUATION = "valuation"
    OTHER = "other"


class SyncStatus(StrEnum):
    """Lifecycle of a sync job row in data_sync_log."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

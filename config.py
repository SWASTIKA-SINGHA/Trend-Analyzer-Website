"""Configuration and environment helpers for Internet Trend Radar."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    news_api_key: str
    default_geo: str = "US"
    default_timeframe: str = "today 3-m"
    default_news_language: str = "en"


def load_config() -> AppConfig:
    """Load runtime configuration from environment variables.

    Returns:
        AppConfig: Immutable app configuration.
    """
    return AppConfig(
        news_api_key=os.getenv("NEWSAPI_KEY", "").strip(),
        default_geo=os.getenv("DEFAULT_GEO", "US").strip() or "US",
        default_timeframe=os.getenv("DEFAULT_TIMEFRAME", "today 3-m").strip() or "today 3-m",
        default_news_language=os.getenv("NEWS_LANGUAGE", "en").strip() or "en",
    )

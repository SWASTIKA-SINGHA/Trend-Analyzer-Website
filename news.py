"""NewsAPI integration for trend-related headlines.

Uses direct HTTP requests to https://newsapi.org/v2/everything so that
no third-party SDK is required beyond the standard ``requests`` library.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

import requests

LOGGER = logging.getLogger(__name__)

# NewsAPI keys are exactly 32 hexadecimal (lowercase) characters.
# Some keys may use full alphanumeric range; accept both forms.
NEWS_API_KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{32}$")
NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"


def validate_news_api_key(api_key: str) -> tuple[bool, str | None]:
    """Return (True, None) when the key looks valid, else (False, reason)."""
    key = (api_key or "").strip()
    if not key:
        return False, "News API key is missing."
    if not NEWS_API_KEY_PATTERN.fullmatch(key):
        return False, "Invalid News API key format. Expected a 32-character alphanumeric key."
    return True, None


class NewsService:
    """Service for fetching trend-related news articles from NewsAPI."""

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_articles(
        self,
        keyword: str,
        language: str = "en",
        page_size: int = 8,
    ) -> tuple[List[Dict[str, str]], str | None]:
        """Fetch recent articles for *keyword* from NewsAPI.

        Uses GET https://newsapi.org/v2/everything?q={keyword}&language=en&sortBy=publishedAt

        Returns ``(articles, None)`` on success or ``([], error_message)`` on failure.
        """
        keyword = keyword.strip()
        if not keyword:
            return [], "Please enter a keyword to fetch related news."

        is_valid, validation_error = validate_news_api_key(self.api_key)
        if not is_valid:
            return [], validation_error or "News API key is not configured."

        try:
            response = requests.get(
                NEWSAPI_EVERYTHING_URL,
                params={
                    "q": keyword,
                    "language": language,
                    "sortBy": "publishedAt",
                    "apiKey": self.api_key,
                    "pageSize": max(1, min(int(page_size), 20)),
                },
                timeout=self.timeout,
            )

            data: dict = response.json()

            if data.get("status") != "ok":
                api_error = data.get("message", "NewsAPI returned a non-ok status.")
                LOGGER.warning("NewsAPI non-ok for keyword=%s: %s", keyword, api_error)
                return [], api_error

            raw_articles: list = data.get("articles", [])
            normalized: List[Dict[str, str]] = []
            for article in raw_articles:
                url = (article.get("url") or "").strip()
                if not url:
                    continue
                normalized.append(
                    {
                        "title": article.get("title") or "Untitled",
                        "source": (article.get("source") or {}).get("name") or "Unknown Source",
                        "url": url,
                        "published_at": article.get("publishedAt") or "",
                        "description": article.get("description") or "No description available.",
                    }
                )

            if not normalized:
                return [], "No related news articles found for this keyword."

            return normalized, None

        except requests.exceptions.Timeout:
            LOGGER.warning("NewsAPI request timed out for keyword=%s", keyword)
            return [], "News request timed out. Please try again."
        except Exception as exc:
            LOGGER.exception("NewsAPI request failed for keyword=%s: %s", keyword, exc)
            return [], "Unable to fetch news articles right now. Please try again later."

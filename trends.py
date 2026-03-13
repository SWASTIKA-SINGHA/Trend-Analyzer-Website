"""Google Trends integration layer."""

from __future__ import annotations

import logging
import time
from typing import List

import pandas as pd
from pytrends.request import TrendReq

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Maps ISO region codes to country names accepted by trending_searches()
REGION_TRENDING_MAP: dict = {
    "US": "united_states",
    "IN": "india",
    "GB": "united_kingdom",
    "CA": "canada",
    "AU": "australia",
}

CURATED_FALLBACK_TOPICS: List[str] = [
    "Artificial Intelligence",
    "ChatGPT",
    "Apple Vision Pro",
    "Quantum Computing",
    "OpenAI",
    "NVIDIA",
    "Bitcoin",
    "Tesla",
    "SpaceX",
    "Cybersecurity",
]


class TrendsService:
    """Service for reading trending topics and keyword interest from Google Trends."""

    def __init__(self, hl: str = "en-US", tz: int = 330) -> None:
        # retries=0 / backoff_factor=0 avoids urllib3-v2 incompatibility with pytrends
        self.pytrends = TrendReq(hl=hl, tz=tz, retries=0, backoff_factor=0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_trending_topics(self, region: str = "IN", top_n: int = 10) -> List[str]:
        """Return the top trending topics for the given region.

        Uses trending_searches(pn=<country_name>) as the primary source with
        today_searches and realtime fallbacks before dropping to a curated list.
        """
        region = (region or "IN").strip().upper()
        pn = REGION_TRENDING_MAP.get(region, "india")

        # Attempt 1: trending_searches with mapped country name
        topics = self._safe_trending_searches(pn)
        if topics:
            LOGGER.info("trending_searches returned %d topics for pn=%s", len(topics), pn)
            return topics[:top_n]

        # Attempt 2: today_searches with ISO code
        topics = self._safe_today_searches(region)
        if topics:
            LOGGER.info("today_searches returned %d topics for region=%s", len(topics), region)
            return topics[:top_n]

        # Attempt 3: realtime trending searches
        topics = self._safe_realtime_searches(region)
        if topics:
            LOGGER.info("realtime_trending_searches returned %d topics for region=%s", len(topics), region)
            return topics[:top_n]

        # Final fallback: curated static list
        LOGGER.warning(
            "All Google Trends trending endpoints failed for region=%s. Using curated fallback.", region
        )
        return CURATED_FALLBACK_TOPICS[:top_n]

    def get_keyword_trend(
        self, keyword: str, region: str = "IN", timeframe: str = "now 7-d"
    ) -> pd.DataFrame:
        """Return keyword popularity over time using pytrends.interest_over_time().

        Tries the requested region+timeframe first, then progressively broader
        geo/timeframe combinations to work around Google rate-limiting.
        Returns a DataFrame with columns [date, popularity].
        """
        keyword = keyword.strip()
        if not keyword:
            return pd.DataFrame(columns=["date", "popularity"])

        region = (region or "IN").strip().upper()

        # Build a deduplicated list of (geo, timeframe) pairs to attempt in order.
        # geo="" means worldwide – often less rate-limited than regional endpoints.
        candidates: list[tuple[str, str]] = [
            (region, timeframe),
            (region, "today 12-m"),
            ("", timeframe),
            ("", "today 12-m"),
        ]
        seen: set = set()
        attempts: list[tuple[str, str]] = []
        for pair in candidates:
            if pair not in seen:
                seen.add(pair)
                attempts.append(pair)

        for geo, tf in attempts:
            try:
                self.pytrends.build_payload(kw_list=[keyword], timeframe=tf, geo=geo)
                df = self.pytrends.interest_over_time()
                if df is not None and not df.empty and keyword in df.columns:
                    df = df.drop(columns=["isPartial"], errors="ignore")
                    LOGGER.info(
                        "interest_over_time OK keyword=%s geo=%s timeframe=%s rows=%d",
                        keyword, geo or "(worldwide)", tf, len(df),
                    )
                    return (
                        df.reset_index()
                        .rename(columns={keyword: "popularity"})[["date", "popularity"]]
                    )
                LOGGER.warning(
                    "interest_over_time empty keyword=%s geo=%s timeframe=%s",
                    keyword, geo or "(worldwide)", tf,
                )
            except Exception as exc:
                LOGGER.warning(
                    "interest_over_time failed keyword=%s geo=%s timeframe=%s: %s",
                    keyword, geo or "(worldwide)", tf, exc,
                )
                time.sleep(2)

        return pd.DataFrame(columns=["date", "popularity"])

    def get_related_keywords(
        self,
        keyword: str,
        region: str = "IN",
        timeframe: str = "now 7-d",
        max_items: int = 4,
    ) -> List[str]:
        """Return top related keywords using pytrends.related_queries().

        Falls back to worldwide (geo="") if the regional endpoint is rate-limited.
        """
        keyword = keyword.strip()
        if not keyword:
            return []

        region = (region or "IN").strip().upper()

        for geo in [region, ""]:
            try:
                self.pytrends.build_payload(kw_list=[keyword], timeframe=timeframe, geo=geo)
                related = self.pytrends.related_queries()
                if not isinstance(related, dict):
                    continue

                bucket = related.get(keyword) or {}
                results: List[str] = []

                for key in ("top", "rising"):
                    frame = bucket.get(key)
                    if frame is None or frame.empty or "query" not in frame.columns:
                        continue
                    for q in frame["query"].head(max_items).tolist():
                        q_str = str(q).strip()
                        if q_str and q_str.lower() != "nan" and q_str not in results:
                            results.append(q_str)
                    if len(results) >= max_items:
                        break

                if results:
                    LOGGER.info(
                        "related_queries OK keyword=%s geo=%s count=%d",
                        keyword, geo or "(worldwide)", len(results),
                    )
                    return results[:max_items]

                LOGGER.warning(
                    "related_queries empty keyword=%s geo=%s", keyword, geo or "(worldwide)"
                )
            except Exception as exc:
                LOGGER.warning(
                    "related_queries failed keyword=%s geo=%s: %s",
                    keyword, geo or "(worldwide)", exc,
                )
                time.sleep(2)

        return []

    def get_interest_for_keywords(
        self,
        keywords: List[str],
        region: str = "IN",
        timeframe: str = "now 7-d",
    ) -> pd.DataFrame:
        """Return interest over time for multiple keywords.

        Returns a long-format DataFrame with columns [date, keyword, popularity].
        """
        clean = [k.strip() for k in keywords if k and k.strip()]
        if not clean:
            return pd.DataFrame(columns=["date", "keyword", "popularity"])

        region = (region or "IN").strip().upper()
        batch = clean[:5]  # pytrends supports up to 5 keywords at once

        # Try region-specific first, fall back to worldwide.
        for geo in [region, ""]:
            try:
                self.pytrends.build_payload(kw_list=batch, timeframe=timeframe, geo=geo)
                df = self.pytrends.interest_over_time()
                if df is not None and not df.empty:
                    df = df.drop(columns=["isPartial"], errors="ignore")
                    LOGGER.info(
                        "get_interest_for_keywords OK geo=%s timeframe=%s rows=%d",
                        geo or "(worldwide)", timeframe, len(df),
                    )
                    return df.reset_index().melt(
                        id_vars=["date"], var_name="keyword", value_name="popularity"
                    )
                LOGGER.warning(
                    "get_interest_for_keywords empty geo=%s timeframe=%s", geo or "(worldwide)", timeframe
                )
            except Exception as exc:
                LOGGER.warning(
                    "get_interest_for_keywords failed geo=%s timeframe=%s: %s",
                    geo or "(worldwide)", timeframe, exc,
                )
                time.sleep(2)

        return pd.DataFrame(columns=["date", "keyword", "popularity"])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_trending_searches(self, pn: str) -> List[str]:
        """Fetch trending_searches and return a clean list of topic strings."""
        try:
            df = self.pytrends.trending_searches(pn=pn)
            if df is None or df.empty:
                return []
            return [
                str(v).strip()
                for v in df.iloc[:, 0].tolist()
                if str(v).strip() and str(v).strip().lower() != "nan"
            ]
        except Exception as exc:
            LOGGER.warning("trending_searches failed pn=%s: %s", pn, exc)
            return []

    def _safe_today_searches(self, region: str) -> List[str]:
        """Fetch today_searches for a region ISO code."""
        try:
            data = self.pytrends.today_searches(pn=region)
            if data is None:
                return []
            if isinstance(data, pd.Series):
                return [str(v).strip() for v in data.tolist() if str(v).strip()]
            if isinstance(data, pd.DataFrame) and not data.empty:
                topics: List[str] = []
                for col in data.columns:
                    for v in data[col].tolist():
                        t = str(v).strip()
                        if t and t.lower() != "nan":
                            topics.append(t)
                return list(dict.fromkeys(topics))
            return []
        except Exception as exc:
            LOGGER.warning("today_searches failed region=%s: %s", region, exc)
            return []

    def _safe_realtime_searches(self, region: str) -> List[str]:
        """Fetch realtime_trending_searches for a region ISO code."""
        try:
            df = self.pytrends.realtime_trending_searches(pn=region)
            if df is None or df.empty:
                return []
            col = "title" if "title" in df.columns else df.columns[0]
            return [
                str(v).strip()
                for v in df[col].tolist()
                if str(v).strip() and str(v).strip().lower() != "nan"
            ]
        except Exception as exc:
            LOGGER.warning("realtime_trending_searches failed region=%s: %s", region, exc)
            return []


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _deduplicated_timeframes(primary: str, fallback: str) -> List[str]:
    """Return [primary] if primary == fallback, else [primary, fallback]."""
    if primary == fallback:
        return [primary]
    return [primary, fallback]

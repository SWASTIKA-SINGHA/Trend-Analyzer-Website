"""Streamlit app entry point for Internet Trend Radar."""

from __future__ import annotations

import logging
import os

import streamlit as st

from graphs import build_interest_line_chart, build_multi_keyword_chart
from news import NewsService, validate_news_api_key
from trends import TrendsService


st.set_page_config(page_title="Internet Trend Radar", page_icon="📈", layout="wide")
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


@st.cache_resource
def get_trends_service() -> TrendsService:
    return TrendsService()


@st.cache_resource
def get_news_service(api_key: str) -> NewsService:
    return NewsService(api_key=api_key)


@st.cache_data(ttl=900)
def fetch_trending_topics(region: str) -> list[str]:
    return get_trends_service().get_trending_topics(region=region, top_n=10)


@st.cache_data(ttl=900)
def fetch_interest_over_time(keyword: str, region: str, timeframe: str):
    return get_trends_service().get_keyword_trend(keyword=keyword, region=region, timeframe=timeframe)


@st.cache_data(ttl=900)
def fetch_related_keywords(keyword: str, region: str, timeframe: str):
    return get_trends_service().get_related_keywords(keyword=keyword, region=region, timeframe=timeframe, max_items=4)


@st.cache_data(ttl=900)
def fetch_multi_interest(keywords: list[str], region: str, timeframe: str):
    return get_trends_service().get_interest_for_keywords(keywords=keywords, region=region, timeframe=timeframe)


@st.cache_data(ttl=600)
def fetch_news(keyword: str, api_key: str):
    return get_news_service(api_key).get_articles(keyword=keyword, language="en", page_size=8)


st.title("Internet Trend Radar")
st.caption("Track trending topics, keyword popularity, and related news in one dashboard.")

region_options = {
    "United States": "US",
    "India": "IN",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
}

def get_news_key_from_secrets() -> str:
    try:
        news_key = st.secrets.get("NEWSAPI_KEY", "")
        return str(news_key).strip() if news_key else ""
    except Exception:
        # Missing secrets file should never crash the dashboard.
        return ""


secret_news_key = get_news_key_from_secrets() or os.getenv("NEWSAPI_KEY", "").strip()

with st.sidebar:
    st.header("Filters")
    selected_region_name = st.selectbox("Region", list(region_options.keys()), index=1)
    region = region_options[selected_region_name]
    timeframe = st.selectbox(
        "Timeframe",
        ["now 7-d", "today 1-m", "today 3-m", "today 12-m", "today 5-y"],
        index=0,
    )
    if secret_news_key:
        st.success("Using NEWSAPI_KEY from Streamlit secrets/environment.")
        news_api_key = secret_news_key
        is_key_valid, key_error = validate_news_api_key(news_api_key)
    else:
        news_api_key = st.text_input("NewsAPI Key", value="", type="password")
        st.caption("Add a valid NewsAPI key to load related articles. Format: 32 alphanumeric characters.")
        is_key_valid, key_error = validate_news_api_key(news_api_key)
        if news_api_key.strip() and not is_key_valid:
            st.error(key_error)
        elif is_key_valid:
            st.success("News API key looks valid.")

    if st.button("Refresh Trends"):
        st.cache_data.clear()

try:
    topics = fetch_trending_topics(region=region)
except Exception as exc:
    LOGGER.exception("Unexpected error while fetching trending topics: %s", exc)
    topics = []

left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    st.subheader("Trending Now")
    if not topics:
        st.info("No trending topics returned right now. Please try Refresh Trends or switch region.")
    else:
        for idx, topic in enumerate(topics, start=1):
            st.write(f"{idx}. {topic}")

default_keyword = topics[0] if topics else "Artificial Intelligence"
keyword = st.text_input("Enter a keyword", value=default_keyword).strip()

with right_col:
    st.subheader("Keyword Popularity Graph")
    if keyword:
        try:
            with st.spinner("Fetching popularity data from Google Trends…"):
                popularity_df = fetch_interest_over_time(
                    keyword=keyword.strip().lower(), region=region, timeframe=timeframe
                )
            if popularity_df.empty:
                st.warning(
                    "No data available for this keyword. Try a more popular keyword."
                )
                # Attempt fallback keyword so the graph section is never blank
                _fallback = "technology"
                if keyword.strip().lower() != _fallback:
                    with st.spinner(f"Trying fallback keyword '{_fallback}'…"):
                        fallback_df = fetch_interest_over_time(
                            keyword=_fallback, region=region, timeframe=timeframe
                        )
                    if not fallback_df.empty:
                        st.info(f"Showing trend data for fallback keyword: **{_fallback}**")
                        st.plotly_chart(
                            build_interest_line_chart(fallback_df, _fallback),
                            use_container_width=True,
                        )
            else:
                fig = build_interest_line_chart(popularity_df, keyword)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            LOGGER.exception("Unexpected error while fetching interest graph for %s: %s", keyword, exc)
            st.error("Could not build popularity graph due to an internal error.")
    else:
        st.info("Enter a keyword to view its popularity graph.")

st.subheader("Related Keywords Trend Comparison")
if keyword:
    try:
        with st.spinner("Fetching related keywords…"):
            related_keywords = fetch_related_keywords(keyword=keyword, region=region, timeframe=timeframe)
        compare_keywords = [keyword] + related_keywords[:3]  # cap at 3 related + the base keyword
        with st.spinner("Building comparison chart…"):
            multi_df = fetch_multi_interest(keywords=compare_keywords, region=region, timeframe=timeframe)
        st.plotly_chart(
            build_multi_keyword_chart(multi_df, f"Trend Comparison: {', '.join(compare_keywords)}"),
            use_container_width=True,
        )
        if related_keywords:
            st.caption(f"Related keywords from Google Trends: {', '.join(related_keywords)}")
        else:
            st.info("No related keywords found. Google Trends may be rate-limiting — click **Refresh Trends** to retry.")
    except Exception as exc:
        LOGGER.exception("Error in Related Keywords section for keyword=%s: %s", keyword, exc)
        st.warning("Could not load related keyword comparison. Please refresh or try a different keyword.")

st.markdown("---")
st.subheader("Related News Articles")
if not keyword:
    st.info("Enter a keyword to load related news.")
elif not news_api_key.strip():
    st.info("Add your NewsAPI key in the sidebar to fetch related news articles.")
elif not is_key_valid:
    st.warning(key_error)
else:
    try:
        with st.spinner("Fetching news articles…"):
            articles, news_error = fetch_news(keyword=keyword, api_key=news_api_key.strip())
        if news_error:
            st.warning(news_error)
        elif not articles:
            st.info("No related news articles found for the selected keyword.")
        else:
            for article in articles:
                st.markdown(f"### [{article['title']}]({article['url']})")
                st.caption(f"Source: **{article['source']}** | Published: {article['published_at']}")
                if article["description"]:
                    st.write(article["description"])
                st.markdown("---")
    except Exception as exc:
        LOGGER.exception("Unexpected error while fetching news for %s: %s", keyword, exc)
        st.error("Unable to fetch news at this time. Please try again later.")

# Internet Trend Radar

Internet Trend Radar is a Streamlit dashboard that fetches trending Google topics and visualizes keyword popularity with Plotly.

## APIs Needed

- NewsAPI key: Required for related news articles.
- Google Trends key: Not required. `pytrends` works without an API key.

## Project Structure

```text
.
├── app.py
├── trends.py
├── graphs.py
├── news.py
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example
└── README.md
```

## Features

- Fetch top 10 trending topics from Google Trends.
- Display trends in a clean dashboard panel.
- Accept custom keyword input.
- Plot keyword popularity over time with an interactive graph.
- Built with Streamlit for a fast web interface.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Streamlit Secrets Setup (Recommended)

Create a local secrets file:

```powershell
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then open `.streamlit/secrets.toml` and set:

```toml
NEWSAPI_KEY = "your_newsapi_key_here"
```

If `NEWSAPI_KEY` is missing in secrets, the app will prompt for it in the sidebar.

## Run

```powershell
streamlit run app.py
```

## Deployment (Streamlit Community Cloud)

1. Push this project to GitHub.
2. Open Streamlit Community Cloud and create a new app from the repo.
3. Set main file path to `app.py`.
4. In app settings, open Secrets and add:

```toml
NEWSAPI_KEY = "your_newsapi_key_here"
```

5. Deploy.

## Expected UI Output

- Title: Internet Trend Radar.
- Left panel: top 10 trending topics.
- Main panel: keyword input, popularity graph, and related-keyword comparison graph.
- Sidebar: region and timeframe selectors.
- Related news section: article title, source, and clickable URL.

## Notes

- If Google Trends rate limits, wait briefly and click Refresh.
- App uses cached responses for better performance.

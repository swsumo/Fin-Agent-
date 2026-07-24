import yfinance as yf
from datetime import datetime, timezone


def fetch_news(ticker, count=10):
    try:
        raw_articles = yf.Ticker(ticker).news or []
    except Exception:
        return []

    articles = []
    for item in raw_articles[:count]:
        content = item.get("content", item)
        headline = content.get("title")
        if not headline:
            continue

        url = (
            (content.get("canonicalUrl") or {}).get("url")
            or (content.get("clickThroughUrl") or {}).get("url")
            or content.get("link")
        )
        published_at = content.get("pubDate") or content.get("providerPublishTime")
        source = (content.get("provider") or {}).get("displayName") or content.get("publisher")

        articles.append({
            "headline": headline,
            "source": source,
            "url": url,
            "published_at": published_at,
            "description": content.get("summary"),
        })

    return articles

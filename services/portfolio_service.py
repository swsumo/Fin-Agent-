import json
from datetime import date

import database
from services import data_service, news_service, groq_service

MAX_HOLDINGS = 8


def run_portfolio_analysis(analysis_id, image_b64=None, mime_type=None, raw_text=None):
    try:
        database.update_portfolio_analysis(analysis_id, status="running", current_step="extracting")

        if image_b64:
            holdings = groq_service.extract_holdings_from_image(image_b64, mime_type)
        else:
            holdings = groq_service.extract_holdings_from_text(raw_text or "")

        holdings = [h for h in holdings if h.get("ticker")][:MAX_HOLDINGS]

        if not holdings:
            database.update_portfolio_analysis(
                analysis_id,
                status="error",
                current_step="extracting",
                error_message="Could not identify any holdings. Try a clearer screenshot, or list them as 'TICKER, avg price, shares' per line.",
            )
            return

        database.update_portfolio_analysis(
            analysis_id,
            current_step="researching",
            holdings_json=json.dumps(holdings),
        )

        enriched = [_enrich_holding(h) for h in holdings]

        database.update_portfolio_analysis(
            analysis_id,
            current_step="synthesizing",
            enrichment_json=json.dumps(enriched),
        )

        analysis = groq_service.analyse_portfolio(enriched, as_of_date=date.today().isoformat())

        database.update_portfolio_analysis(
            analysis_id,
            status="done",
            current_step="complete",
            analysis_json=json.dumps(analysis),
        )
    except Exception as e:
        database.update_portfolio_analysis(analysis_id, status="error", error_message=str(e))


def _enrich_holding(holding):
    ticker = holding["ticker"].upper()
    price_data = data_service.fetch_price_data(ticker)

    if not price_data:
        return {**holding, "ticker": ticker, "error": f"'{ticker}' not found — skipped."}

    company_info = data_service.fetch_company_info(ticker)
    fundamentals = data_service.fetch_fundamentals(ticker)
    news = news_service.fetch_news(ticker, count=3)
    sentiment = groq_service.analyse_sentiment_batch([a["headline"] for a in news])

    current_price = price_data.get("current_price")
    avg_price = holding.get("avg_price")
    unrealized_pl_pct = None
    if current_price and avg_price:
        unrealized_pl_pct = round((current_price - avg_price) / avg_price * 100, 2)

    enriched = {
        "ticker": ticker,
        "avg_price": avg_price,
        "shares": holding.get("shares"),
        "current_price": current_price,
        "unrealized_pl_pct": unrealized_pl_pct,
        "sector": company_info.get("sector"),
        "currency": company_info.get("currency", "USD"),
        "day_change_pct": price_data.get("day_change_pct"),
        "pe_ratio": fundamentals.get("pe_ratio"),
        "revenue_growth": fundamentals.get("revenue_growth"),
        "overall_sentiment": sentiment.get("overall_sentiment"),
    }

    prediction = groq_service.predict_verdict(
        subject=f"{ticker} position (avg cost ${avg_price}, {holding.get('shares')} shares)",
        facts=enriched,
        options=["BUY MORE", "HOLD", "SELL", "TRIM"],
    )
    enriched["predicted_recommendation"] = prediction["verdict"]
    enriched["predicted_reasoning"] = prediction["reasoning"]
    return enriched

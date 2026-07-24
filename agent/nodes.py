import json
import time

import database
from services import data_service, news_service, groq_service, dcf_service, report_service


def _log(report_id, step_name, input_data, output_data, start_time):
    duration_ms = int((time.time() - start_time) * 1000)
    database.log_agent_step(
        report_id, step_name,
        json.dumps(input_data, default=str),
        json.dumps(output_data, default=str),
        duration_ms,
    )


def collect_data_node(state):
    start_time = time.time()
    ticker = state["ticker"]
    report_id = state["report_id"]

    company_info = data_service.fetch_company_info(ticker)
    if not company_info:
        error = f"Ticker '{ticker}' not found. Try AAPL, MSFT, TCS.NS, RELIANCE.NS"
        state["errors"] = state.get("errors", []) + [error]
        database.update_report(report_id, status="error", current_step="data_collected", error_message=error)
        _log(report_id, "collect_data", {"ticker": ticker}, {"error": error}, start_time)
        return state

    price_data = data_service.fetch_price_data(ticker)
    fundamentals = data_service.fetch_fundamentals(ticker)

    state["company_name"] = company_info.get("company_name", ticker)
    state["price_data"] = price_data
    state["fundamentals"] = fundamentals
    state["ratios"] = fundamentals
    state["current_step"] = "data_collected"

    database.update_report(
        report_id,
        status="running",
        current_step="data_collected",
        company_name=state["company_name"],
        price_data=json.dumps({**price_data, **company_info}),
        fundamentals=json.dumps(fundamentals),
    )
    _log(report_id, "collect_data", {"ticker": ticker}, {"company_info": company_info, "price_data": price_data}, start_time)
    return state


def analyse_news_node(state):
    if state.get("errors"):
        return state

    start_time = time.time()
    ticker = state["ticker"]
    report_id = state["report_id"]

    articles = news_service.fetch_news(ticker, count=10)
    headlines = [a["headline"] for a in articles]
    sentiment_result = groq_service.analyse_sentiment_batch(headlines)
    labels = sentiment_result["labels"]

    for article, label in zip(articles, labels):
        article["sentiment"] = label

    positive = labels.count("Positive")
    negative = labels.count("Negative")
    if not labels:
        overall_sentiment = "No data"
    elif positive > negative:
        overall_sentiment = "Bullish"
    elif negative > positive:
        overall_sentiment = "Bearish"
    else:
        overall_sentiment = "Neutral"

    state["news_articles"] = articles
    state["sentiment_summary"] = sentiment_result["overall_sentiment"]
    state["overall_sentiment"] = overall_sentiment
    state["current_step"] = "news_analysed"

    database.update_report(
        report_id,
        current_step="news_analysed",
        news_json=json.dumps({
            "articles": articles,
            "sentiment_summary": sentiment_result["overall_sentiment"],
            "overall_sentiment": overall_sentiment,
        }),
    )
    _log(report_id, "analyse_news", {"ticker": ticker, "headline_count": len(headlines)}, sentiment_result, start_time)
    return state


def analyse_financials_node(state):
    if state.get("errors"):
        return state

    start_time = time.time()
    report_id = state["report_id"]
    fundamentals = state.get("fundamentals", {})
    sector = None

    analysis = groq_service.analyse_financials(fundamentals, sector)

    state["strengths"] = analysis["strengths"]
    state["risks"] = analysis["risks"]
    state["bull_case"] = analysis["bull_case"]
    state["bear_case"] = analysis["bear_case"]
    state["current_step"] = "financials_analysed"

    database.update_report(
        report_id,
        current_step="financials_analysed",
        analysis_json=json.dumps(analysis),
    )
    _log(report_id, "analyse_financials", {"fundamentals": fundamentals}, analysis, start_time)
    return state


def dcf_estimation_node(state):
    if state.get("errors"):
        return state

    start_time = time.time()
    ticker = state["ticker"]
    report_id = state["report_id"]
    fundamentals = state.get("fundamentals", {})
    current_price = (state.get("price_data") or {}).get("current_price")

    dcf_result = dcf_service.estimate_dcf_from_fundamentals(fundamentals, current_price)
    commentary = groq_service.generate_dcf_commentary(ticker, dcf_result)

    state["dcf_intrinsic_value"] = dcf_result.get("intrinsic_value")
    state["dcf_margin_of_safety"] = dcf_result.get("margin_of_safety")
    state["dcf_verdict"] = dcf_result.get("verdict", "UNAVAILABLE")
    state["dcf_commentary"] = commentary
    state["dcf_assumptions"] = dcf_result.get("assumptions_used")
    state["current_step"] = "dcf_complete"

    database.update_report(
        report_id,
        current_step="dcf_complete",
        dcf_json=json.dumps({**dcf_result, "commentary": commentary}),
    )
    _log(report_id, "dcf_estimation", {"fundamentals": fundamentals, "current_price": current_price}, dcf_result, start_time)
    return state


def predict_verdict_node(state):
    if state.get("errors"):
        return state

    start_time = time.time()
    report_id = state["report_id"]
    fundamentals = state.get("fundamentals", {})

    facts = {
        "current_price": (state.get("price_data") or {}).get("current_price"),
        "day_change_pct": (state.get("price_data") or {}).get("day_change_pct"),
        "pe_ratio": fundamentals.get("pe_ratio"),
        "revenue_growth": fundamentals.get("revenue_growth"),
        "profit_margin": fundamentals.get("profit_margin"),
        "debt_to_equity": fundamentals.get("debt_to_equity"),
        "strengths": state.get("strengths"),
        "risks": state.get("risks"),
        "overall_sentiment": state.get("overall_sentiment"),
        "dcf_verdict": state.get("dcf_verdict"),
        "dcf_margin_of_safety": state.get("dcf_margin_of_safety"),
    }

    prediction = groq_service.predict_verdict(
        subject=f"{state['ticker']} ({state.get('company_name', '')})",
        facts=facts,
        options=["BUY", "HOLD", "SELL"],
    )

    state["predicted_verdict"] = prediction["verdict"]
    state["predicted_verdict_reasoning"] = prediction["reasoning"]
    state["current_step"] = "verdict_predicted"

    database.update_report(report_id, current_step="verdict_predicted")
    _log(report_id, "predict_verdict", facts, prediction, start_time)
    return state


def write_report_node(state):
    if state.get("errors"):
        return state

    start_time = time.time()
    report_id = state["report_id"]

    report_data = {
        "ticker": state["ticker"],
        "company_name": state.get("company_name"),
        "price_data": state.get("price_data"),
        "fundamentals": state.get("fundamentals"),
        "strengths": state.get("strengths"),
        "risks": state.get("risks"),
        "bull_case": state.get("bull_case"),
        "bear_case": state.get("bear_case"),
        "overall_sentiment": state.get("overall_sentiment"),
        "sentiment_summary": state.get("sentiment_summary"),
        "dcf_intrinsic_value": state.get("dcf_intrinsic_value"),
        "dcf_margin_of_safety": state.get("dcf_margin_of_safety"),
        "dcf_verdict": state.get("dcf_verdict"),
        "dcf_commentary": state.get("dcf_commentary"),
        "predicted_verdict": state.get("predicted_verdict"),
        "predicted_verdict_reasoning": state.get("predicted_verdict_reasoning"),
    }

    report_json = groq_service.write_report(report_data)
    report_html = report_service.build_report_html(state, report_json)

    state["final_report_json"] = report_json
    state["final_report_html"] = report_html
    state["current_step"] = "report_complete"

    database.update_report(
        report_id,
        status="done",
        current_step="report_complete",
        report_json=json.dumps(report_json),
        report_html=report_html,
    )
    _log(report_id, "write_report", {"ticker": state["ticker"]}, report_json, start_time)
    return state

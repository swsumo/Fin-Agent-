import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = "qwen/qwen3.6-27b"
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client


def call_groq(system_prompt, user_prompt, max_tokens=1000):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return _chat_completion(messages, max_tokens)


def call_groq_vision(system_prompt, user_prompt, image_base64, mime_type, max_tokens=1000):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
        ],
    })
    return _chat_completion(messages, max_tokens)


def _chat_completion(messages, max_tokens):
    for attempt in range(2):
        try:
            response = _get_client().chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.4,
                reasoning_effort="none",
            )
            return response.choices[0].message.content.strip()
        except Exception:
            if attempt == 1:
                raise


def _extract_json(raw, default=None):
    try:
        raw = raw.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        return json.loads(raw)
    except (ValueError, AttributeError):
        return default


def analyse_sentiment_batch(headlines):
    if not headlines:
        return {"labels": [], "overall_sentiment": "No recent news available."}

    headlines = headlines[:10]
    numbered = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
    prompt = (
        "Analyse these financial news headlines. For each, return exactly one "
        "label: Positive, Negative, or Neutral, one per line in the same order "
        "with no numbering or extra text. After the labels, add a line '---' "
        "followed by one sentence giving the overall market sentiment.\n\n"
        + numbered
    )

    try:
        raw = call_groq(None, prompt, max_tokens=300)
        parts = raw.split("---")
        label_lines = [line.strip(" .\t") for line in parts[0].splitlines() if line.strip()]

        labels = []
        for i in range(len(headlines)):
            label = label_lines[i].capitalize() if i < len(label_lines) else "Neutral"
            labels.append(label if label in ("Positive", "Negative", "Neutral") else "Neutral")

        overall_sentiment = parts[1].strip() if len(parts) > 1 else "Sentiment summary unavailable."
        return {"labels": labels, "overall_sentiment": overall_sentiment}
    except Exception:
        return {"labels": ["Neutral"] * len(headlines), "overall_sentiment": "Sentiment analysis unavailable."}


def analyse_financials(fundamentals_dict, sector):
    fundamentals_dict = fundamentals_dict or {}
    fallback = {
        "strengths": [],
        "risks": [],
        "bull_case": "Bull case unavailable — insufficient data or analysis failed.",
        "bear_case": "Bear case unavailable — insufficient data or analysis failed.",
    }

    system_prompt = (
        "You are a professional equity research analyst. Respond with ONLY valid "
        "JSON, no markdown fences, no preamble, matching exactly this shape: "
        '{"strengths": ["...", "..."], "risks": ["...", "..."], '
        '"bull_case": "2 sentence bull thesis", "bear_case": "2 sentence bear thesis"}'
    )
    user_prompt = (
        f"Sector: {sector}\n"
        f"Fundamentals:\n"
        + "\n".join(f"- {key}: {value}" for key, value in fundamentals_dict.items() if value is not None)
    )

    try:
        raw = call_groq(system_prompt, user_prompt, max_tokens=500)
        parsed = _extract_json(raw)
        if not parsed:
            return fallback
        return {
            "strengths": parsed.get("strengths") or [],
            "risks": parsed.get("risks") or [],
            "bull_case": parsed.get("bull_case") or fallback["bull_case"],
            "bear_case": parsed.get("bear_case") or fallback["bear_case"],
        }
    except Exception:
        return fallback


def predict_verdict(subject, facts, options):
    """The single prediction agent: turns a set of facts into one decisive
    call from `options`, with reasoning. Every BUY/HOLD/SELL-type decision
    in the app routes through here, so the narrative-writing agents below
    (write_report, analyse_portfolio) never re-decide a verdict themselves —
    they're told what was predicted and asked to write consistently with it.
    """
    default_verdict = "HOLD" if "HOLD" in options else options[0]
    fallback = {"verdict": default_verdict, "reasoning": "Insufficient data to form a confident prediction."}

    system_prompt = (
        f"You are a decisive investment prediction agent. Given the facts below "
        f"about {subject}, choose exactly ONE verdict from this list: "
        f"{', '.join(options)}. Do not hedge with multiple options. Respond with "
        f"ONLY valid JSON, no markdown fences, no preamble: "
        f'{{"verdict": "one of {options}", "reasoning": "2-3 sentences citing '
        f'the specific figures below that justify this call"}}'
    )
    user_prompt = "\n".join(f"{key}: {value}" for key, value in facts.items() if value is not None)

    try:
        raw = call_groq(system_prompt, user_prompt, max_tokens=300)
        parsed = _extract_json(raw)
        if not parsed:
            return fallback
        verdict = str(parsed.get("verdict") or "").strip().upper()
        if verdict not in [o.upper() for o in options]:
            verdict = default_verdict
        else:
            verdict = next(o for o in options if o.upper() == verdict)
        return {
            "verdict": verdict,
            "reasoning": parsed.get("reasoning") or fallback["reasoning"],
        }
    except Exception:
        return fallback


def generate_dcf_commentary(ticker, dcf_result):
    if not dcf_result.get("available"):
        return dcf_result.get("reason", "DCF unavailable.")

    prompt = (
        f"In exactly 2 short sentences, interpret this DCF valuation for {ticker}: "
        f"intrinsic value ${dcf_result['intrinsic_value']}, current price "
        f"${dcf_result['current_price']}, margin of safety {dcf_result['margin_of_safety']}% "
        f"(positive means undervalued, negative means overvalued). The verdict is "
        f"{dcf_result['verdict']}. State the verdict plainly and mention one key risk "
        f"that could invalidate it."
    )
    try:
        return call_groq(None, prompt, max_tokens=150)
    except Exception:
        return f"Verdict: {dcf_result['verdict']} (commentary unavailable)."


def write_report(report_data):
    predicted_verdict = report_data.get("predicted_verdict", "HOLD")
    predicted_reasoning = report_data.get("predicted_verdict_reasoning", "")

    fallback = {
        "executive_summary": "Report generation unavailable — Groq did not return a valid response.",
        "company_overview": "",
        "financial_highlights": [],
        "bull_case": report_data.get("bull_case", ""),
        "bear_case": report_data.get("bear_case", ""),
        "news_impact": report_data.get("sentiment_summary", ""),
        "dcf_commentary": report_data.get("dcf_commentary", ""),
        "investment_verdict": predicted_verdict,
        "verdict_reasoning": predicted_reasoning or "Insufficient data to form a confident verdict.",
        "key_metrics_to_watch": [],
    }

    system_prompt = (
        "You are a professional equity research analyst writing the narrative "
        "for a structured investment research report. The investment verdict "
        f"has already been decided by a separate prediction agent: {predicted_verdict}, "
        f"because: {predicted_reasoning}. Do not choose a different verdict — "
        "write 'investment_verdict' as exactly that value, and write "
        "'verdict_reasoning' as a fuller elaboration consistent with it. "
        "Respond with ONLY valid JSON, no markdown fences, no preamble, "
        "matching exactly these keys: "
        '{"executive_summary": "3-4 sentence overview", '
        '"company_overview": "2-3 sentence company description", '
        '"financial_highlights": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"], '
        '"bull_case": "3-4 sentence bull thesis", '
        '"bear_case": "3-4 sentence bear thesis", '
        '"news_impact": "2-3 sentence news sentiment summary", '
        '"dcf_commentary": "2-3 sentence valuation commentary", '
        f'"investment_verdict": "{predicted_verdict}", '
        '"verdict_reasoning": "2 sentence reasoning for verdict", '
        '"key_metrics_to_watch": ["metric 1", "metric 2", "metric 3"]}'
    )
    user_prompt = "\n".join(f"{key}: {value}" for key, value in report_data.items() if value)

    try:
        raw = call_groq(system_prompt, user_prompt, max_tokens=1200)
        parsed = _extract_json(raw)
        if not parsed:
            return fallback
        merged = dict(fallback)
        merged.update({k: v for k, v in parsed.items() if v})
        merged["investment_verdict"] = predicted_verdict
        return merged
    except Exception:
        return fallback


def extract_holdings_from_image(image_base64, mime_type):
    system_prompt = (
        "You are a financial data extraction assistant. Look at this image of a "
        "brokerage or portfolio holdings screen. Extract every position you can "
        "identify. Respond with ONLY valid JSON, no markdown fences, no preamble: "
        '{"holdings": [{"ticker": "AAPL", "avg_price": 150.0, "shares": 10}]}. '
        "Use the stock ticker symbol if visible; if only a company name is shown, "
        "infer the most likely ticker. If a field truly isn't visible, use null "
        "for it rather than guessing a number."
    )
    try:
        raw = call_groq_vision(system_prompt, "Extract the holdings from this image.", image_base64, mime_type, max_tokens=800)
        parsed = _extract_json(raw, default={"holdings": []})
        return parsed.get("holdings") or []
    except Exception:
        return []


def extract_holdings_from_text(raw_text):
    system_prompt = (
        "You are a financial data extraction assistant. The user will paste text "
        "describing their stock holdings (any format — freeform, comma separated, "
        "one per line). Extract every position. Respond with ONLY valid JSON, no "
        "markdown fences, no preamble: "
        '{"holdings": [{"ticker": "AAPL", "avg_price": 150.0, "shares": 10}]}. '
        "Use the stock ticker symbol; if only a company name is given, infer the "
        "most likely ticker. If a field isn't given, use null rather than guessing."
    )
    try:
        raw = call_groq(system_prompt, raw_text, max_tokens=800)
        parsed = _extract_json(raw, default={"holdings": []})
        return parsed.get("holdings") or []
    except Exception:
        return []


def analyse_portfolio(enriched_holdings, as_of_date):
    predicted = {h["ticker"]: h.get("predicted_recommendation", "HOLD") for h in enriched_holdings}
    fallback = {
        "portfolio_summary": "Portfolio analysis unavailable — Groq did not return a valid response.",
        "overall_market_context": "",
        "holdings": [
            {
                "ticker": h.get("ticker"),
                "recommendation": h.get("predicted_recommendation", "HOLD"),
                "reasoning": h.get("predicted_reasoning") or "Analysis unavailable.",
            }
            for h in enriched_holdings
        ],
        "historical_parallel": "",
        "overall_recommendation": "Unable to form a confident recommendation with the data available.",
    }

    system_prompt = (
        "You are a seasoned portfolio manager giving a client a frank, specific "
        "review of their holdings — the kind of analysis that would satisfy a "
        "professional, not vague generalities. Reference the actual numbers you "
        "are given (current price, avg cost, unrealised P/L, sector, recent "
        "sentiment) in your reasoning for each position. Each holding already "
        "has a 'predicted_recommendation' decided by a separate prediction "
        "agent — use that exact value as 'recommendation' for that ticker, do "
        "not choose a different call; write 'reasoning' as your own fuller "
        "elaboration consistent with it. You may note parallels to past market "
        "episodes from your own knowledge, but explicitly frame these as "
        "general historical context and reasoning, not as certainty or "
        "backtested fact. Respond with ONLY valid JSON, no markdown fences, no "
        "preamble, matching exactly these keys: "
        '{"portfolio_summary": "3-4 sentence overview of the whole portfolio", '
        '"overall_market_context": "2-3 sentences on current market trends relevant to these holdings", '
        '"holdings": [{"ticker": "AAPL", "recommendation": "(use the given predicted_recommendation)", '
        '"reasoning": "2-3 sentences citing specific figures"}], '
        '"historical_parallel": "2-3 sentences noting any historical parallel, framed as general reasoning", '
        '"overall_recommendation": "2-3 sentence overall verdict for the portfolio as a whole"}'
    )
    user_prompt = f"As of {as_of_date}. Holdings:\n" + json.dumps(enriched_holdings, default=str)

    try:
        raw = call_groq(system_prompt, user_prompt, max_tokens=1500)
        parsed = _extract_json(raw)
        if not parsed:
            return fallback
        merged = dict(fallback)
        merged.update({k: v for k, v in parsed.items() if v})
        for holding in merged.get("holdings", []):
            if holding.get("ticker") in predicted:
                holding["recommendation"] = predicted[holding["ticker"]]
        return merged
    except Exception:
        return fallback

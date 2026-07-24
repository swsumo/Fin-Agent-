from datetime import datetime, timezone
from html import escape

VERDICT_COLORS = {"BUY": "#2ecc71", "SELL": "#e63950", "HOLD": "#888"}
CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "GBP": "£", "EUR": "€", "JPY": "¥"}


def _list_html(items):
    if not items:
        return "<p>—</p>"
    return "<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in items) + "</ul>"


def build_report_html(state, report_json):
    ticker = escape(state.get("ticker", ""))
    company_name = escape(state.get("company_name") or ticker)
    price_data = state.get("price_data") or {}
    verdict = report_json.get("investment_verdict", "HOLD").upper()
    verdict_color = VERDICT_COLORS.get(verdict, "#888")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    currency_symbol = CURRENCY_SYMBOLS.get(price_data.get("currency"), "$")
    current_price = price_data.get("current_price")
    price_display = f"{currency_symbol}{current_price}" if current_price is not None else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{ticker} — Finsight Research Report</title>
<style>
  body {{ background:#1a1a1a; color:#f0f0f0; font-family:-apple-system,Segoe UI,Roboto,sans-serif; max-width:820px; margin:0 auto; padding:32px 20px; }}
  h1 {{ margin-bottom:0; }}
  .muted {{ color:#888; }}
  .verdict {{ display:inline-block; padding:6px 16px; border-radius:100px; font-weight:700; color:#fff; background:{verdict_color}; }}
  section {{ margin-top:28px; }}
  .label {{ text-transform:uppercase; font-size:11px; letter-spacing:1px; color:#888; margin-bottom:8px; }}
  .card {{ background:#232323; border:1px solid #333; border-radius:8px; padding:18px 22px; }}
</style>
</head>
<body>
  <h1>{ticker} — {company_name}</h1>
  <p class="muted">Generated {generated_at} · Current price: {price_display}</p>
  <span class="verdict">{verdict}</span>
  <p>{escape(report_json.get('verdict_reasoning', ''))}</p>

  <section>
    <div class="label">Executive Summary</div>
    <div class="card">{escape(report_json.get('executive_summary', ''))}</div>
  </section>

  <section>
    <div class="label">Company Overview</div>
    <div class="card">{escape(report_json.get('company_overview', ''))}</div>
  </section>

  <section>
    <div class="label">Financial Highlights</div>
    <div class="card">{_list_html(report_json.get('financial_highlights'))}</div>
  </section>

  <section>
    <div class="label">Bull Case</div>
    <div class="card">{escape(report_json.get('bull_case', ''))}</div>
  </section>

  <section>
    <div class="label">Bear Case</div>
    <div class="card">{escape(report_json.get('bear_case', ''))}</div>
  </section>

  <section>
    <div class="label">News Impact</div>
    <div class="card">{escape(report_json.get('news_impact', ''))}</div>
  </section>

  <section>
    <div class="label">DCF Valuation</div>
    <div class="card">{escape(report_json.get('dcf_commentary', ''))}</div>
  </section>

  <section>
    <div class="label">Key Metrics to Watch</div>
    <div class="card">{_list_html(report_json.get('key_metrics_to_watch'))}</div>
  </section>
</body>
</html>"""

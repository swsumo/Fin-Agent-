import yfinance as yf


def fetch_company_info(ticker):
    info = yf.Ticker(ticker).info
    if not info or not info.get("symbol"):
        return {}

    return {
        "company_name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "employees": info.get("fullTimeEmployees"),
    }


def fetch_price_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")
    if hist.empty:
        return {}

    current_price = float(hist["Close"].iloc[-1])

    def change_pct(days):
        if len(hist) <= days:
            return None
        past_price = float(hist["Close"].iloc[-1 - days])
        if not past_price:
            return None
        return round((current_price - past_price) / past_price * 100, 2)

    info = stock.info or {}

    return {
        "current_price": round(current_price, 2),
        "day_change_pct": change_pct(1),
        "week_change_pct": change_pct(5),
        "month_change_pct": change_pct(21),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "volume": int(hist["Volume"].iloc[-1]) if not hist["Volume"].empty else None,
        "avg_volume": info.get("averageVolume"),
    }


def fetch_fundamentals(ticker):
    info = yf.Ticker(ticker).info
    if not info or not info.get("symbol"):
        return {}

    return {
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
        "eps": info.get("trailingEps"),
        "revenue": info.get("totalRevenue"),
        "revenue_growth": info.get("revenueGrowth"),
        "profit_margin": info.get("profitMargins"),
        "gross_margin": info.get("grossMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "free_cash_flow": info.get("freeCashflow"),
        "shares_outstanding": info.get("sharesOutstanding"),
    }

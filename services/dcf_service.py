DEFAULT_WACC = 0.10
DEFAULT_TERMINAL_GROWTH = 0.03
DEFAULT_FCF_MARGIN = 0.15
PROJECTION_YEARS = 5
GROWTH_CAP = 0.30
GROWTH_FLOOR = -0.10


def estimate_dcf_from_fundamentals(fundamentals, current_price):
    revenue = fundamentals.get("revenue")
    shares_outstanding = fundamentals.get("shares_outstanding")

    if not revenue or not shares_outstanding:
        return {
            "available": False,
            "reason": "DCF unavailable — insufficient financial data (missing revenue or shares outstanding).",
        }

    raw_growth = fundamentals.get("revenue_growth") or 0.10
    growth_rate = max(GROWTH_FLOOR, min(GROWTH_CAP, raw_growth))

    free_cash_flow = fundamentals.get("free_cash_flow")
    fcf_margin = (free_cash_flow / revenue) if free_cash_flow and revenue else DEFAULT_FCF_MARGIN
    fcf_margin = max(fcf_margin, 0.01)

    projected_revenue = revenue
    discounted_cash_flows = []
    fcf_final_year = 0

    for year in range(1, PROJECTION_YEARS + 1):
        projected_revenue *= (1 + growth_rate)
        fcf = projected_revenue * fcf_margin
        discounted_cash_flows.append(fcf / ((1 + DEFAULT_WACC) ** year))
        fcf_final_year = fcf

    terminal_value = fcf_final_year * (1 + DEFAULT_TERMINAL_GROWTH) / (DEFAULT_WACC - DEFAULT_TERMINAL_GROWTH)
    discounted_terminal_value = terminal_value / ((1 + DEFAULT_WACC) ** PROJECTION_YEARS)

    enterprise_value = sum(discounted_cash_flows) + discounted_terminal_value
    intrinsic_value = enterprise_value / shares_outstanding

    margin_of_safety = None
    verdict = "UNKNOWN"
    if current_price:
        margin_of_safety = round((intrinsic_value - current_price) / intrinsic_value * 100, 2)
        if margin_of_safety > 15:
            verdict = "UNDERVALUED"
        elif margin_of_safety < -15:
            verdict = "OVERVALUED"
        else:
            verdict = "FAIRLY VALUED"

    return {
        "available": True,
        "intrinsic_value": round(intrinsic_value, 2),
        "current_price": current_price,
        "margin_of_safety": margin_of_safety,
        "verdict": verdict,
        "assumptions_used": {
            "growth_rate": round(growth_rate * 100, 2),
            "wacc": round(DEFAULT_WACC * 100, 2),
            "terminal_growth": round(DEFAULT_TERMINAL_GROWTH * 100, 2),
            "years": PROJECTION_YEARS,
            "fcf_margin": round(fcf_margin * 100, 2),
        },
    }

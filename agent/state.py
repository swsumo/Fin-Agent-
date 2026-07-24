from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    ticker: str
    report_id: int
    company_name: str
    current_step: str
    errors: List[str]

    # Step 1 outputs
    price_data: dict
    fundamentals: dict
    ratios: dict

    # Step 2 outputs
    news_articles: List[dict]
    sentiment_summary: str
    overall_sentiment: str

    # Step 3 outputs
    strengths: List[str]
    risks: List[str]
    bull_case: str
    bear_case: str

    # Step 4 outputs
    dcf_intrinsic_value: Optional[float]
    dcf_margin_of_safety: Optional[float]
    dcf_verdict: Optional[str]
    dcf_commentary: Optional[str]
    dcf_assumptions: Optional[dict]

    # Step 5 outputs (prediction agent)
    predicted_verdict: Optional[str]
    predicted_verdict_reasoning: Optional[str]

    # Step 6 outputs (report writer)
    final_report_html: Optional[str]
    final_report_json: Optional[dict]

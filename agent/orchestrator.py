from langgraph.graph import StateGraph, START, END

import database
from agent.state import AgentState
from agent.nodes import (
    collect_data_node,
    analyse_news_node,
    analyse_financials_node,
    dcf_estimation_node,
    predict_verdict_node,
    write_report_node,
)

_graph = StateGraph(AgentState)
_graph.add_node("collect_data", collect_data_node)
_graph.add_node("analyse_news", analyse_news_node)
_graph.add_node("analyse_financials", analyse_financials_node)
_graph.add_node("dcf_estimation", dcf_estimation_node)
_graph.add_node("predict_verdict", predict_verdict_node)
_graph.add_node("write_report", write_report_node)

_graph.add_edge(START, "collect_data")
_graph.add_edge("collect_data", "analyse_news")
_graph.add_edge("analyse_news", "analyse_financials")
_graph.add_edge("analyse_financials", "dcf_estimation")
_graph.add_edge("dcf_estimation", "predict_verdict")
_graph.add_edge("predict_verdict", "write_report")
_graph.add_edge("write_report", END)

compiled_graph = _graph.compile()


def run_agent(ticker, report_id):
    initial_state = {
        "ticker": ticker,
        "report_id": report_id,
        "company_name": "",
        "current_step": "queued",
        "errors": [],
    }
    try:
        compiled_graph.invoke(initial_state)
    except Exception as e:
        database.update_report(report_id, status="error", error_message=str(e))

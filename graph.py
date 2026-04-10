from langgraph.graph import END, START, StateGraph

from agents import (
    BizSenseState,
    analysis_agent,
    orchestrator_agent,
    report_agent,
    research_agent,
)


def build_bizsense_graph():
    workflow = StateGraph(BizSenseState)

    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("research", research_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("report", report_agent)

    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("orchestrator", "research")
    workflow.add_edge("research", "analysis")
    workflow.add_edge("analysis", "report")
    workflow.add_edge("report", END)

    return workflow.compile()

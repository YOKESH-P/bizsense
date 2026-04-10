import os
from typing import Any, Dict, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from tavily import TavilyClient

load_dotenv()


class BizSenseState(TypedDict, total=False):
    topic: str
    user_context: str
    orchestrator_plan: str
    research_notes: str
    analysis_content: str
    final_report: str
    current_agent: str


def _llm() -> ChatAnthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment")
    return ChatAnthropic(model="claude-sonnet-4-6", anthropic_api_key=api_key, temperature=0.2)


def orchestrator_agent(state: BizSenseState) -> Dict[str, Any]:
    topic = state.get("topic", "").strip()
    if not topic:
        return {"orchestrator_plan": "Missing topic", "current_agent": "orchestrator"}

    prompt = f"""
You are BizSense Orchestrator Agent.
Create a concise execution plan for business intelligence analysis on: "{topic}".
Plan should include:
1) what market data to gather
2) what competitors to evaluate
3) which SWOT dimensions to focus on
4) what strategic outcomes to optimize
Return as short bullet points.
"""
    response = _llm().invoke(prompt)
    return {"orchestrator_plan": response.content, "current_agent": "orchestrator"}


def research_agent(state: BizSenseState) -> Dict[str, Any]:
    topic = state.get("topic", "").strip()
    plan = state.get("orchestrator_plan", "")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY is not set in environment")

    tavily_client = TavilyClient(api_key=tavily_api_key)
    search_results = tavily_client.search(
        query=f"{topic} market size trends competitors challenges opportunities",
        search_depth="advanced",
        max_results=6,
    )
    result_lines = []
    for item in search_results.get("results", []):
        title = item.get("title", "Untitled")
        content = item.get("content", "")
        url = item.get("url", "")
        result_lines.append(f"- {title}\n  {content}\n  Source: {url}")
    web_context = "\n".join(result_lines) if result_lines else "No web findings available."

    prompt = f"""
You are BizSense Research Agent.
Topic: {topic}
Plan: {plan}

Synthesize the following web findings into structured research notes:
{web_context}

Return sections:
- Market data points
- Key competitors
- Industry trends
- Source-backed evidence
"""
    response = _llm().invoke(prompt)
    return {"research_notes": response.content, "current_agent": "research"}


def analysis_agent(state: BizSenseState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    research_notes = state.get("research_notes", "")
    prompt = f"""
You are BizSense Analysis Agent.
Build a deep analysis for "{topic}" using the research notes below.

{research_notes}

Must include:
1. Executive Summary
2. Market Overview
3. Competitor Analysis
4. SWOT Analysis
5. Growth Opportunities
6. Risks and Challenges
7. Strategic Recommendations

Use clear headings and practical, business-oriented insights.
"""
    response = _llm().invoke(prompt)
    return {"analysis_content": response.content, "current_agent": "analysis"}


def report_agent(state: BizSenseState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    analysis_content = state.get("analysis_content", "")
    prompt = f"""
You are BizSense Report Agent.
Create a polished, comprehensive final business intelligence report for "{topic}".

Base content:
{analysis_content}

Requirements:
- Keep all required sections
- Add concise action-oriented bullet points in recommendations
- Ensure professional executive tone
- Produce markdown output
"""
    response = _llm().invoke(prompt)
    return {"final_report": response.content, "current_agent": "report"}

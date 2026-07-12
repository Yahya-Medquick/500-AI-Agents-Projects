"""
Web Research Agent using LangGraph + Tavily Search.

Searches the web for a given topic, synthesizes findings, generates a PDF,
and outputs a Base64 payload for direct UI downloads.
"""

import argparse
import base64
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from fpdf import FPDF
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()


class ResearchState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    search_results: list[dict]
    report: str


def search_web(state: ResearchState) -> ResearchState:
    tool = TavilySearch(max_results=5)
    raw_results = tool.invoke(state["query"])
    if isinstance(raw_results, dict):
        results = raw_results.get("results", [])
    elif isinstance(raw_results, list):
        results = raw_results
    else:
        results = []
    return {"search_results": results}


def synthesize_report(state: ResearchState) -> ResearchState:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    llm = ChatOpenAI(
        model="gemini-2.5-flash",
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        temperature=0
    )

    results_text = "\n\n".join(
        f"Source: {r.get('url', 'N/A')}\nTitle: {r.get('title', 'N/A')}\nContent: {r.get('content', '')[:500]}"
        for r in state["search_results"]
    )

    messages = [
        SystemMessage(content="You are a research analyst. Synthesize the search results into a clear, structured report with: Summary, Key Findings (bullet points), and Sources."),
        HumanMessage(content=f"Research query: {state['query']}\n\nSearch results:\n{results_text}"),
    ]

    response = llm.invoke(messages)
    return {"report": response.content, "messages": [response]}


def save_as_pdf(text: str, filename: str = "research_report.pdf") -> str:
    """Generates a clean PDF document using fpdf2 write() for automatic line wrapping."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    
    # Sanitize characters to prevent latin-1 encoding errors
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    
    # pdf.write() handles auto-wrapping across margins natively
    pdf.write(5, clean_text)
    pdf.output(filename)
    return filename


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("search", search_web)
    graph.add_node("synthesize", synthesize_report)
    graph.set_entry_point("search")
    graph.add_edge("search", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def main():
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("--query", default=None, help="Research query")
    args = parser.parse_args()

    # Prioritize: CLI argument -> Environment Variable -> Fallback Default
    query = args.query or os.getenv("TASK_PROMPT") or "latest advances in AI agents 2024"

    agent = build_graph()
    result = agent.invoke({"query": query, "messages": [], "search_results": [], "report": ""})

    report_content = result["report"]

    # Print output flanked by delimiter tags for clean UI extraction
    print("\n---REPORT_START---")
    print(report_content)
    print("---REPORT_END---\n")

    # Generate PDF file safely
    pdf_filename = "research_report.pdf"
    save_as_pdf(report_content, pdf_filename)

    # Output Base64 payload for direct UI download
    if os.path.exists(pdf_filename):
        with open(pdf_filename, "rb") as f:
            b64_pdf = base64.b64encode(f.read()).decode("utf-8")
            print("\n---PDF_BASE64_START---")
            print(b64_pdf)
            print("---PDF_BASE64_END---\n")


if __name__ == "__main__":
    main()

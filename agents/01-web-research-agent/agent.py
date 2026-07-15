"""
Web Research Agent with On-Demand Document Exporters (PDF, DOCX, PPTX, PY).
"""

import argparse
import base64
import os
import re
from typing import Annotated, TypedDict

from docx import Document
from dotenv import load_dotenv
from fpdf import FPDF
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_tavily import TavilySearch
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pptx import Presentation

# Import the key rotator helper at the top
from scripts.gemini_rotator import get_gemini_llm

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
    # Replaced manual ChatOpenAI with rotator helper + gemini-3.5-flash
    llm = get_gemini_llm(model="gemini-3.5-flash", temperature=0)

    results_text = "\n\n".join(
        f"Source: {r.get('url', 'N/A')}\nTitle: {r.get('title', 'N/A')}\nContent: {r.get('content', '')[:500]}"
        for r in state["search_results"]
    )

    messages = [
        SystemMessage(content=(
            "You are a research analyst. Synthesize the search results into a clear, structured Markdown report "
            "with: Summary, Key Findings (bullet points), and Sources. "
            "IMPORTANT: Output ONLY the research text/markdown. Do NOT write Python scripts, code blocks, or instructions on how to create documents."
        )),
        HumanMessage(content=f"Research query: {state['query']}\n\nSearch results:\n{results_text}"),
    ]

    response = llm.invoke(messages)
    return {"report": response.content, "messages": [response]}


# --- ON-DEMAND EXPORT FUNCTIONS ---

def export_pdf(text: str, filename: str = "report.pdf") -> str:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.write(5, clean_text)
    pdf.output(filename)
    return filename


def export_docx(text: str, filename: str = "report.docx") -> str:
    doc = Document()
    doc.add_heading("Research Report", level=1)
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    doc.save(filename)
    return filename


def export_pptx(text: str, filename: str = "report.pptx") -> str:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Research Report Summary"
    slide.placeholders[1].text = text[:1200]
    prs.save(filename)
    return filename


def export_python(text: str, filename: str = "script.py") -> str:
    code_match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    code_content = code_match.group(1) if code_match else text
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code_content)
    return filename


def handle_on_demand_export(prompt: str, report_text: str):
    prompt_lower = prompt.lower()
    generated_file = None

    if any(k in prompt_lower for k in ["docx", "word", "doc"]):
        generated_file = export_docx(report_text)
    elif "pdf" in prompt_lower:
        generated_file = export_pdf(report_text)
    elif any(k in prompt_lower for k in ["pptx", "presentation", "slides", "powerpoint"]):
        generated_file = export_pptx(report_text)
    elif "export code" in prompt_lower or "generate python script" in prompt_lower:
        generated_file = export_python(report_text)

    if generated_file and os.path.exists(generated_file):
        with open(generated_file, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")
            print(f"\n---FILE_EXPORT_START:{generated_file}---")
            print(b64_str)
            print("---FILE_EXPORT_END---\n")


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

    query = args.query or os.getenv("TASK_PROMPT") or "latest advances in AI agents"

    agent = build_graph()
    result = agent.invoke({"query": query, "messages": [], "search_results": [], "report": ""})

    report_content = result["report"]

    print("\n---REPORT_START---")
    print(report_content)
    print("---REPORT_END---\n")

    handle_on_demand_export(query, report_content)


if __name__ == "__main__":
    main()

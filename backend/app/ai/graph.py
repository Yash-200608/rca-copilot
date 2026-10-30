"""The LangGraph workflow.

    START -> route -+- full_analysis -> extract_incident -> find_similar -+
                    +- analyze ------------------------------------------+
                                                                         +-> fishbone ---+
                                                                         +-> five_whys --+-> root_cause -> evidence_gaps -> capa -> impact -> summarize
                    +- capa -> capa -> summarize                                          (join: waits for both branches)
                    +- gaps -> evidence_gaps -> summarize
                    +- summarize -> summarize
                    +- edit -> edit -> END
                    +- question -> answer -> END
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .common import RCAState, skippable
from .nodes.analysis import capa, evidence_gaps, find_similar, fishbone, five_whys, impact, root_cause, summarize
from .nodes.chat import answer, edit, no_source, route
from .nodes.extract import extract_incident


NEEDS_SOURCE = ("full_analysis", "analyze")


def _pick(state: RCAState) -> str:
    intent = state.get("intent", "full_analysis")
    if intent in NEEDS_SOURCE and not state.get("source_text", "").strip():
        return "no_source"
    return intent


def build_graph():
    g = StateGraph(RCAState)
    for name, fn in [("route", route), ("extract_incident", extract_incident), ("find_similar", find_similar),
                     ("fishbone", fishbone), ("five_whys", five_whys), ("root_cause", root_cause),
                     ("evidence_gaps", evidence_gaps), ("capa", capa), ("impact", impact), ("summarize", summarize),
                     ("edit", edit), ("answer", answer), ("no_source", no_source)]:
        g.add_node(name, skippable(fn))
    g.add_edge(START, "route")
    g.add_conditional_edges("route", _pick, {
        "full_analysis": "extract_incident", "analyze": "find_similar", "capa": "capa", "gaps": "evidence_gaps",
        "summarize": "summarize", "edit": "edit", "question": "answer", "no_source": "no_source",
    })
    g.add_edge("extract_incident", "find_similar")
    g.add_edge("find_similar", "fishbone")      # fan-out: two analyses run in parallel
    g.add_edge("find_similar", "five_whys")
    g.add_edge(["fishbone", "five_whys"], "root_cause")  # fan-in: join
    g.add_edge("root_cause", "evidence_gaps")
    # evidence_gaps feeds capa in the full flow; for the 'gaps' intent we stop at the summary
    g.add_conditional_edges("evidence_gaps", lambda s: "capa" if s.get("intent") in ("full_analysis", "analyze") else "summarize",
                            {"capa": "capa", "summarize": "summarize"})
    g.add_conditional_edges("capa", lambda s: "impact" if s.get("intent") in ("full_analysis", "analyze") else "summarize",
                            {"impact": "impact", "summarize": "summarize"})
    g.add_edge("impact", "summarize")
    g.add_edge("summarize", END)
    g.add_edge("edit", END)
    g.add_edge("answer", END)
    g.add_edge("no_source", END)
    return g.compile()


GRAPH = build_graph()


def mermaid() -> str:
    return GRAPH.get_graph().draw_mermaid()


from langgraph.graph import END, START, StateGraph

from agents.editor import editor_node
from agents.strategist import strategist_node
from agents.writer import writer_node
from graph.state import CreatorState


def route_after_editor(state: CreatorState) -> str:
    if state["approved"]:
        return "finish"

    if state["revision_count"] >= state["max_revisions"]:
        return "finish"

    return "revise"


def build_creator_graph():
    builder = StateGraph(CreatorState)

    builder.add_node("strategist", strategist_node)
    builder.add_node("writer", writer_node)
    builder.add_node("editor", editor_node)

    builder.add_edge(START, "strategist")
    builder.add_edge("strategist", "writer")
    builder.add_edge("writer", "editor")

    builder.add_conditional_edges(
        "editor",
        route_after_editor,
        {
            "revise": "writer",
            "finish": END,
        },
    )

    return builder.compile()

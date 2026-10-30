from langgraph.graph import END, START, StateGraph

from agents.editor import editor_node
from agents.evaluator import initial_evaluator_node, final_evaluator_node
from agents.strategist import strategist_node
from agents.writer import writer_node
from graph.state import CreatorState


def route_after_editor(state: CreatorState) -> str:
    if state["approved"] or state["revision_count"] >= state["max_revisions"]:
        return "evaluate_final"
    return "revise"


def build_creator_graph():
    builder = StateGraph(CreatorState)
    builder.add_node("strategist", strategist_node)
    builder.add_node("writer", writer_node)
    builder.add_node("initial_evaluator", initial_evaluator_node)
    builder.add_node("editor", editor_node)
    builder.add_node("final_evaluator", final_evaluator_node)

    builder.add_edge(START, "strategist")
    builder.add_edge("strategist", "writer")
    builder.add_edge("writer", "initial_evaluator")
    builder.add_edge("initial_evaluator", "editor")
    builder.add_conditional_edges(
        "editor", route_after_editor,
        {"revise": "writer", "evaluate_final": "final_evaluator"},
    )
    builder.add_edge("final_evaluator", END)
    return builder.compile()
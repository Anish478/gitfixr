from langgraph.graph import StateGraph, END
from pipeline.state import AgentState
from pipeline.agents.code_reader import code_reader
from pipeline.agents.planner    import planner
from pipeline.agents.code_writer import code_writer
from pipeline.agents.pr_opener  import pr_opener


def build_graph():
    """
    Builds and compiles the Phase 2 pipeline:
        code_reader → planner → code_writer → pr_opener → END

    How LangGraph works:
    - Each node receives the FULL AgentState dict
    - Each node returns a PARTIAL dict (only the keys it changed)
    - LangGraph merges each partial result back into the state before calling the next node
    """
    graph = StateGraph(AgentState)

    graph.add_node("code_reader", code_reader)
    graph.add_node("planner",     planner)
    graph.add_node("code_writer", code_writer)
    graph.add_node("pr_opener",   pr_opener)

    graph.set_entry_point("code_reader")
    graph.add_edge("code_reader", "planner")
    graph.add_edge("planner",     "code_writer")
    graph.add_edge("code_writer", "pr_opener")
    graph.add_edge("pr_opener",   END)

    return graph.compile()
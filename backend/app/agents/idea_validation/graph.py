from langgraph.graph import StateGraph, START, END

from .state import ValidationState
from .nodes import (
    search_reddit,
    search_trends,
    search_competitors,
    judge_logic,
)
from .timing import log_timing


def create_validation_graph() -> StateGraph:
    """
    Create the validation pipeline graph.
    
    Structure:
    START -> [search_reddit, search_trends, search_competitors] (parallel)
          -> judge_logic
          -> END
    
    All nodes are async and will run concurrently where graph edges allow.
    """
    log_timing("graph", "Creating validation graph")
    
    # Initialize the graph with our state schema
    graph = StateGraph(ValidationState)
    
    graph.add_node("search_reddit", search_reddit)
    graph.add_node("search_trends", search_trends)
    graph.add_node("search_competitors", search_competitors)
    graph.add_node("judge_logic", judge_logic)
        
    # Parallel execution: all three search nodes start immediately
    graph.add_edge(START, "search_reddit")
    graph.add_edge(START, "search_trends")
    graph.add_edge(START, "search_competitors")
    
    # All search nodes feed into judge
    graph.add_edge("search_reddit", "judge_logic")
    graph.add_edge("search_trends", "judge_logic")
    graph.add_edge("search_competitors", "judge_logic")
    
    graph.add_edge("judge_logic", END)
    
    return graph


validation_graph = create_validation_graph().compile()

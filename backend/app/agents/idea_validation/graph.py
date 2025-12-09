from langgraph.graph import StateGraph, START, END

from .state import ValidationState
from .nodes import (
    search_reddit,
    search_trends,
    search_competitors,
    judge_logic,
)


def create_validation_graph() -> StateGraph:

    # Initialize the graph with our state schema
    graph = StateGraph(ValidationState)
    
    graph.add_node("search_reddit", search_reddit)
    graph.add_node("search_trends", search_trends)
    graph.add_node("search_competitors", search_competitors)
    graph.add_node("judge_logic", judge_logic)
    
    graph.add_edge(START, "search_reddit")
    graph.add_edge(START, "search_trends")
    graph.add_edge(START, "search_competitors")
    
    graph.add_edge("search_reddit", "judge_logic")
    graph.add_edge("search_trends", "judge_logic")
    graph.add_edge("search_competitors", "judge_logic")
    
    graph.add_edge("judge_logic", END)
    
    return graph


validation_graph = create_validation_graph().compile()




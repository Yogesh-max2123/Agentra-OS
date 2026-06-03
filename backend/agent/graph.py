from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from agent.state import AgentState
from agent.nodes import chatbot_node
from agent.tools import travel_tools

workflow = StateGraph(AgentState)

# Nodes add karna
workflow.add_node("agent", chatbot_node)
tool_node = ToolNode(travel_tools)
workflow.add_node("tools", tool_node)

# Flow patterns setup karna
workflow.add_edge(START, "agent")

# Conditional routing basis LLM tool calls intent
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)

workflow.add_edge("tools", "agent")

nexus_graph = workflow.compile()
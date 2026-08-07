"""
Compiles a WorkflowSpec (YAML, see /workflows) into an executable
LangGraph StateGraph.

See docs/architecture.md §8 for the full design writeup this
implements.
"""

import yaml
from langgraph.graph import StateGraph, START, END

# TODO: swap for a durable, Postgres-backed checkpointer before any
# non-local use. See docs/architecture.md §3 and §15.
from langgraph.checkpoint.memory import InMemorySaver


def build_graph(spec_yaml: str, node_registry, routing_registry):
    spec = yaml.safe_load(spec_yaml)
    StateSchema = _build_typed_dict(spec["state_schema"])

    builder = StateGraph(StateSchema)

    for node in spec["nodes"]:
        handler = node_registry.resolve(node)
        builder.add_node(node["id"], handler)

    for edge in spec.get("edges", []):
        src = START if edge["from"] == "START" else edge["from"]
        dst = END if edge["to"] == "END" else edge["to"]
        builder.add_edge(src, dst)

    for route in spec.get("routes", []):
        if "condition" in route:
            route_fn = routing_registry.resolve(route["condition"])
            builder.add_conditional_edges(route["from"], route_fn, route["targets"])
        else:
            dst = END if route["to"] == "END" else route["to"]
            builder.add_edge(route["from"], dst)

    checkpointer = InMemorySaver()  # TODO: PostgresSaver in non-local envs
    return builder.compile(checkpointer=checkpointer)


def _build_typed_dict(state_schema: dict):
    """Dynamically builds a TypedDict from the YAML state_schema block."""
    from typing import TypedDict

    type_map = {"str": str, "bool": bool, "int": int, "float": float}
    annotations = {
        field: type_map.get(type_name, str)
        for field, type_name in state_schema.items()
    }
    return TypedDict("WorkflowState", annotations, total=False)

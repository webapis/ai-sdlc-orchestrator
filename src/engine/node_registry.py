"""
Maps a WorkflowSpec node's `type` (agent / function / human / subgraph)
to an executable node function.

See docs/architecture.md §8.2-8.3.
"""

from langgraph.types import interrupt


class NodeRegistry:
    def __init__(self):
        self._functions = {}
        self._roles = {}

    def register_function(self, name, fn, *, idempotent: bool = False):
        # TODO: enforce idempotency requirement per docs/architecture.md §9.3
        # for any function node with an external side effect.
        self._functions[name] = fn

    def register_role(self, name, role_config):
        self._roles[name] = role_config

    def resolve(self, node_spec):
        node_type = node_spec["type"]
        if node_type == "agent":
            role = self._roles[node_spec["role"]]
            return _make_agent_node(role, node_spec)
        if node_type == "function":
            return self._functions[node_spec["handler"]]
        if node_type == "human":
            return _make_human_node(node_spec)
        if node_type == "subgraph":
            raise NotImplementedError("subgraph nodes: not yet implemented")
        raise ValueError(f"Unknown node type: {node_type}")


def _make_agent_node(role, node_spec):
    def agent_node(state):
        # TODO: build the model call from role.system_prompt + role.tools,
        # using role.output_schema to structure the return value.
        raise NotImplementedError("agent node execution: not yet implemented")

    return agent_node


def _make_human_node(node_spec):
    def human_node(state):
        context = {field: state.get(field) for field in node_spec["context_fields"]}
        decision = interrupt(
            {
                "message": f"Approval required at node '{node_spec['id']}'.",
                "context": context,
                "allowed_actions": node_spec["allowed_actions"],
            }
        )
        return {"human_approved": decision.get("action") == "approve"}

    return human_node

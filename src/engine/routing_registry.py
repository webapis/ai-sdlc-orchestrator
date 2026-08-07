"""
Named routing/guard functions referenced by `condition:` in workflow
specs. Kept in code (not YAML) so hard business logic, like revision
caps, is tested rather than configured.

See docs/architecture.md §6.3.
"""


class RoutingRegistry:
    def __init__(self):
        self._routes = {
            "route_after_test": route_after_test,
            "route_after_human": route_after_human,
        }

    def resolve(self, name):
        return self._routes[name]


def route_after_test(state):
    """Used by workflows/feature-development.yaml."""
    if state.get("revision_count", 0) >= 3:  # limits.revision_count_max
        return "human_approval"
    if state.get("tests_passed") and state.get("review_approved"):
        return "human_approval"
    return "revise"


def route_after_human(state):
    return "merge" if state.get("human_approved") else "revise"

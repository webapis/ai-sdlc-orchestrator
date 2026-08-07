"""
Failure classification and retry/escalation policy.
See docs/architecture.md §9.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class FailureCategory(str, Enum):
    TRANSIENT_NETWORK = "transient_network"
    RATE_LIMIT = "rate_limit"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    POLICY_VIOLATION = "policy_violation"
    MODEL_FORMAT_ERROR = "model_format_error"
    UNKNOWN = "unknown"


@dataclass
class RetryPolicy:
    max_attempts: int
    backoff: Optional[str] = None
    wait_for_reset: bool = False
    action: Optional[str] = None


RETRY_POLICY = {
    FailureCategory.TRANSIENT_NETWORK: RetryPolicy(max_attempts=3, backoff="exponential"),
    FailureCategory.RATE_LIMIT: RetryPolicy(
        max_attempts=5, backoff="exponential", wait_for_reset=True
    ),
    FailureCategory.INVALID_INPUT: RetryPolicy(
        max_attempts=0, action="return_to_validation"
    ),
    FailureCategory.PERMISSION_DENIED: RetryPolicy(
        max_attempts=0, action="escalate_to_human"
    ),
    FailureCategory.POLICY_VIOLATION: RetryPolicy(max_attempts=0, action="stop_run"),
    FailureCategory.MODEL_FORMAT_ERROR: RetryPolicy(
        max_attempts=2, action="repair_output"
    ),
    FailureCategory.UNKNOWN: RetryPolicy(max_attempts=0, action="escalate_to_human"),
}


def classify(exc: Exception) -> FailureCategory:
    # TODO: real classification logic based on exception type / provider
    # error codes. See docs/architecture.md §9.1.
    return FailureCategory.UNKNOWN

"""Built-in challenge template identifiers for Cortex."""

BUILTIN_CHALLENGE_TEMPLATES = {
    "null_inputs": "Require tests for None/null/empty inputs and missing optional fields.",
    "boundary_values": "Require tests at min/max/zero/one/off-by-one boundaries.",
    "error_handling": "Require tests for expected failure paths and exception handling.",
    "graveyard_regression": "Require tests covering relevant previously failed approaches.",
}

__all__ = ["BUILTIN_CHALLENGE_TEMPLATES"]

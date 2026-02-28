from __future__ import annotations

from cortex.stop_contract import resolve_stop_contract


def test_resolve_stop_contract_uses_structured_cortex_stop() -> None:
    contract = resolve_stop_contract(
        {
            "cortex_stop": {
                "challenge_coverage": {"null_inputs": True},
                "required_requirement_ids": ["R1", "R2"],
            }
        },
        allow_message_fallback=True,
        require_structured_stop_payload=True,
    )
    assert contract.challenge_coverage == {"null_inputs": True}
    assert contract.required_requirement_ids == ["R1", "R2"]
    assert contract.structured_stop_violation is False


def test_resolve_stop_contract_flags_trailer_only_when_structured_required() -> None:
    contract = resolve_stop_contract(
        {
            "last_assistant_message": (
                'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true}}'
            )
        },
        allow_message_fallback=True,
        require_structured_stop_payload=True,
    )
    assert contract.challenge_coverage == {"null_inputs": True}
    assert contract.structured_stop_violation is True


def test_resolve_stop_contract_normalizes_failed_approach_aliases() -> None:
    contract = resolve_stop_contract(
        {
            "what_was_tried": "single-pass parser",
            "why_failed": "edge cases skipped",
            "failed_files": ["src/parser.py"],
        },
        allow_message_fallback=True,
        require_structured_stop_payload=False,
    )
    assert contract.failed_approach == {
        "summary": "single-pass parser",
        "reason": "edge cases skipped",
        "files": ["src/parser.py"],
    }


def test_resolve_stop_contract_drops_incomplete_failed_approach() -> None:
    contract = resolve_stop_contract(
        {
            "failed_approach": {"summary": "tried regex parser"},
        },
        allow_message_fallback=True,
        require_structured_stop_payload=False,
    )
    assert contract.failed_approach is None


def test_resolve_stop_contract_reads_failed_approach_aliases_from_cortex_stop() -> None:
    contract = resolve_stop_contract(
        {
            "cortex_stop": {
                "what_was_tried": "single-pass parser",
                "why_failed": "edge cases skipped",
                "failed_files": ["src/parser.py"],
            }
        },
        allow_message_fallback=True,
        require_structured_stop_payload=False,
    )
    assert contract.failed_approach == {
        "summary": "single-pass parser",
        "reason": "edge cases skipped",
        "files": ["src/parser.py"],
    }


def test_resolve_stop_contract_reads_failed_approach_aliases_from_message_fallback() -> None:
    contract = resolve_stop_contract(
        {
            "last_assistant_message": (
                'CORTEX_STOP_JSON: {"what_was_tried":"single-pass parser","why_failed":"edge cases skipped",'
                '"failed_files":["src/parser.py"]}'
            )
        },
        allow_message_fallback=True,
        require_structured_stop_payload=False,
    )
    assert contract.failed_approach == {
        "summary": "single-pass parser",
        "reason": "edge cases skipped",
        "files": ["src/parser.py"],
    }

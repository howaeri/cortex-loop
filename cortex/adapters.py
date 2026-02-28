from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class NormalizedEvent:
    name: str
    payload: dict[str, Any]


class EventAdapter(Protocol):
    def normalize(self, event_name: str, payload: Mapping[str, Any] | None = None) -> NormalizedEvent: ...


class _MappingAdapter:
    EVENT_ALIASES: dict[str, str] = {}

    def normalize(self, event_name: str, payload: Mapping[str, Any] | None = None) -> NormalizedEvent:
        return NormalizedEvent(
            name=self._normalize_event_name(event_name),
            payload=self._normalize_payload(payload),
        )

    def _normalize_event_name(self, event_name: str) -> str:
        token = event_name.strip().lower().replace("-", "_")
        return self.EVENT_ALIASES.get(token) or self.EVENT_ALIASES.get(token.replace("_", "")) or token

    @staticmethod
    def _normalize_payload(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        for key in ("tool_name", "tool", "toolName", "action"):
            if data.get("tool_name") is None and isinstance(data.get(key), str):
                data["tool_name"] = data[key]
        return data


class ClaudeCodeAdapter(_MappingAdapter):
    EVENT_ALIASES = {
        "sessionstart": "session_start",
        "session_start": "session_start",
        "pretooluse": "pre_tool_use",
        "pre_tool_use": "pre_tool_use",
        "posttooluse": "post_tool_use",
        "post_tool_use": "post_tool_use",
        "stop": "stop",
    }


class AiderAdapter(_MappingAdapter):
    EVENT_ALIASES = {
        "session_start": "session_start",
        "start": "session_start",
        "pre_tool_use": "pre_tool_use",
        "before_tool": "pre_tool_use",
        "post_tool_use": "post_tool_use",
        "after_tool": "post_tool_use",
        "stop": "stop",
        "done": "stop",
    }

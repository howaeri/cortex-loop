# Agent Event Schema

Cortex core consumes provider-neutral normalized events:

- `session_start`
- `pre_tool_use`
- `post_tool_use`
- `stop`

Normalized payload conventions:
- `session_id` (string)
- `tool_name` (string, for tool events)
- provider-specific fields preserved as pass-through

## Adapter boundary

Providers are mapped at `cortex/adapters.py`.

Current adapters:
- `ClaudeCodeAdapter`
- `AiderAdapter` (minimal normalization)

Core routing (`CortexKernel.dispatch`) only accepts normalized event names.
Provider alias handling belongs in adapter layer, not kernel logic.

Example normalized payload:

```json
{
  "session_id": "sess-123",
  "tool_name": "Write",
  "target_files": ["src/app.ts"]
}
```

## Why this matters

- decouples hook payload quirks from enforcement logic
- reduces regressions when provider payload shapes evolve
- keeps contract tests provider-agnostic

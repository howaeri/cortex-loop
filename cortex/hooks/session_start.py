from __future__ import annotations

import argparse
import json
import sys

from cortex.core import CortexKernel


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = _read_stdin_json()
        kernel = CortexKernel(root=args.root, config_path=args.config, adapter_name=args.adapter)
        result = kernel.dispatch("session_start", payload)
        print(json.dumps(result))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "ok": False,
                    "hook": "SessionStart",
                    "error": str(exc),
                }
            )
        )
        return 1


def _read_stdin_json() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Hook payload must be a JSON object")
    return data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", default=".")
    parser.add_argument("--config")
    parser.add_argument("--adapter", choices=["claude", "aider"], default="claude")
    return parser.parse_args([] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

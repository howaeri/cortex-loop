from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .adapters import AiderAdapter, ClaudeCodeAdapter, EventAdapter
from .challenges import ChallengeEnforcer, ChallengeReport
from .foundation import FoundationAnalyzer
from .genome import CortexGenome, load_genome
from .graveyard import Graveyard
from .invariants import InvariantRunner
from .requirements import evaluate_requirement_audit_payload
from .stop_contract import reconcile_required_requirement_ids, resolve_stop_contract
from .stop_policy import compute_stop_outcome
from .store import SQLiteStore
from .utils import _as_bool, _as_string_list, _unique_list


@dataclass(slots=True)
class KernelContext:
    root: Path
    genome_path: Path
    db_path: Path
    genome: CortexGenome
    store: SQLiteStore


class CortexKernel:
    """Hook-driven orchestration kernel for Cortex subsystems."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
        db_path: str | Path | None = None,
        adapter_name: str | None = None,
        adapter: EventAdapter | None = None,
    ) -> None:
        repo_root = Path(root or os.getcwd()).resolve()
        genome_path = Path(config_path).resolve() if config_path else repo_root / "cortex.toml"
        store = SQLiteStore(Path(db_path).resolve() if db_path else repo_root / ".cortex" / "cortex.db")
        store.initialize()
        genome = load_genome(genome_path)
        self.ctx = KernelContext(
            root=repo_root,
            genome_path=genome_path,
            db_path=store.db_path,
            genome=genome,
            store=store,
        )
        self.foundation = FoundationAnalyzer(repo_root, genome.foundation)
        self.graveyard = Graveyard(store, genome.graveyard)
        self.challenges = ChallengeEnforcer(store, genome.challenges)
        self.invariants = InvariantRunner(repo_root, store, genome.invariants, genome.hooks)
        self.adapter = adapter or _resolve_adapter(adapter_name)

    def on_session_start(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = self.adapter.normalize("session_start", payload).payload
        session_id = self._session_id(payload)
        required_requirement_ids = self._extract_required_requirement_ids(payload)
        session_metadata: dict[str, Any] = {"hook": "SessionStart"}
        if required_requirement_ids:
            session_metadata["required_requirement_ids"] = required_requirement_ids
        self.ctx.store.upsert_session_start(
            session_id=session_id,
            status="running",
            genome_path=self.ctx.genome.source_path,
            metadata=session_metadata,
        )
        self._record_event(session_id, "SessionStart", payload)

        foundation_report = self.foundation.analyze()
        task_summary = str(payload.get("task") or payload.get("objective") or "")
        target_files = _as_string_list(payload.get("target_files"))
        graveyard_matches = [m.to_dict() for m in self.graveyard.find_similar(task_summary, target_files)]
        repomap_summary = self._session_start_repomap(session_id=session_id, payload=payload)

        warnings = list(foundation_report.warnings)
        if self.ctx.genome.parse_error:
            warnings.append(f"Config parse error in {self.ctx.genome.source_path}: {self.ctx.genome.parse_error}")
        if graveyard_matches:
            warnings.append(f"Found {len(graveyard_matches)} graveyard match(es) relevant to this session.")
            warnings.extend(self._graveyard_explainability_warnings(graveyard_matches))
        if repomap_summary and repomap_summary.get("warning"):
            warnings.append(str(repomap_summary["warning"]))

        return self._response(
            hook="SessionStart",
            session_id=session_id,
            warnings=warnings,
            foundation=foundation_report.to_dict(),
            graveyard_matches=graveyard_matches,
            repomap=repomap_summary,
            required_requirement_ids=required_requirement_ids,
        )

    def on_pre_tool_use(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = self.adapter.normalize("pre_tool_use", payload).payload
        session_id = self._session_id(payload)
        self._record_event(
            session_id,
            "PreToolUse",
            payload,
            tool_name=str(payload.get("tool_name") or "") or None,
            status=str(payload.get("status")) if payload.get("status") is not None else None,
        )

        warnings: list[str] = []
        target_files = _as_string_list(payload.get("target_files")) + _as_string_list(payload.get("planned_files"))
        if target_files:
            warnings.extend(self.foundation.warnings_for_target_files(target_files))

        return self._response(
            hook="PreToolUse",
            session_id=session_id,
            warnings=warnings,
            proceed=True,
        )

    def on_post_tool_use(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = self.adapter.normalize("post_tool_use", payload).payload
        session_id = self._session_id(payload)
        self._record_event(
            session_id,
            "PostToolUse",
            payload,
            tool_name=str(payload.get("tool_name") or "") or None,
            status=str(payload.get("status")) if payload.get("status") is not None else None,
        )

        warnings: list[str] = []
        if str(payload.get("status", "")).lower() in {"error", "failed", "fail"}:
            summary = str(payload.get("error") or payload.get("message") or "")
            target_files = _as_string_list(payload.get("target_files"))
            matches = self.graveyard.find_similar(summary, target_files, max_matches=3)
            if matches:
                warnings.append(
                    f"Tool failure resembles {len(matches)} graveyard entry/entries; review before retrying."
                )
                warnings.extend(self._graveyard_explainability_warnings([m.to_dict() for m in matches]))
        return self._response(hook="PostToolUse", session_id=session_id, warnings=warnings, proceed=True)

    def on_stop(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = self.adapter.normalize("stop", payload).payload
        session_id = self._session_id(payload)
        self._record_event(session_id, "Stop", payload)

        stop_contract = resolve_stop_contract(
            payload,
            allow_message_fallback=self.ctx.genome.hooks.allow_message_stop_fallback,
            require_structured_stop_payload=self.ctx.genome.hooks.require_structured_stop_payload,
        )
        warnings = list(stop_contract.warnings)

        challenge_report: ChallengeReport | None = None
        coverage_payload = stop_contract.challenge_coverage
        missing_challenge_coverage = False
        if isinstance(coverage_payload, Mapping):
            challenge_report = self.challenges.evaluate(session_id=session_id, coverage_payload=coverage_payload)
            if not challenge_report.ok:
                warnings.append(
                    "Missing challenge coverage for categories: "
                    + ", ".join(challenge_report.missing_categories)
                )
            warnings.extend(challenge_report.config_warnings)
        elif coverage_payload is not None:
            missing_challenge_coverage = self.ctx.genome.challenges.require_coverage
            warnings.append("Invalid challenge_coverage format; expected an object mapping category names to values.")
        elif self.ctx.genome.challenges.require_coverage:
            missing_challenge_coverage = True
            warnings.append(
                "No challenge_coverage provided in Stop payload; skipping challenge gate recording. "
                "Include challenge_coverage or a CORTEX_STOP_JSON trailer in the final assistant message."
            )

        required_requirement_ids, requirement_ids_source, required_ids_warning = (
            reconcile_required_requirement_ids(
                self._session_required_requirement_ids(session_id),
                list(stop_contract.required_requirement_ids),
            )
        )
        if required_ids_warning:
            warnings.append(required_ids_warning)

        requirement_audit = evaluate_requirement_audit_payload(
            stop_contract.requirement_audit,
            require_requirement_audit=self.ctx.genome.hooks.require_requirement_audit,
            require_evidence_for_passed_requirement=self.ctx.genome.hooks.require_evidence_for_passed_requirement,
            required_requirement_ids=required_requirement_ids,
            root=self.ctx.root,
            witness=self._session_witness_context(session_id),
        )
        warnings.extend(requirement_audit.warnings)

        invariant_report = None
        if self.ctx.genome.invariants.run_on_stop and _as_bool(payload.get("run_invariants"), True):
            extra_args = _as_string_list(payload.get("pytest_args"))
            invariant_report = self.invariants.run(session_id=session_id, extra_pytest_args=extra_args)
            if not invariant_report.ok:
                warnings.append("Invariant suite reported failures.")

        if stop_contract.failed_approach:
            self.graveyard.record_failure(
                session_id=session_id,
                summary=str(stop_contract.failed_approach["summary"]),
                reason=str(stop_contract.failed_approach["reason"]),
                files=_as_string_list(stop_contract.failed_approach.get("files")),
            )

        structured_stop_violation = stop_contract.structured_stop_violation
        challenge_ok = None if challenge_report is None else challenge_report.ok
        invariant_ok = None if invariant_report is None else invariant_report.ok
        session_status, recommend_revert = compute_stop_outcome(
            mode=self.ctx.genome.hooks.mode,
            fail_on_missing_challenge_coverage=self.ctx.genome.hooks.fail_on_missing_challenge_coverage,
            fail_on_requirement_audit_gap=self.ctx.genome.hooks.fail_on_requirement_audit_gap,
            require_requirement_audit=self.ctx.genome.hooks.require_requirement_audit,
            challenge_ok=challenge_ok,
            invariant_ok=invariant_ok,
            invariant_recommend_revert=bool(invariant_report and invariant_report.recommend_revert),
            missing_challenge_coverage=missing_challenge_coverage,
            requirement_audit_gap=requirement_audit.gap,
            requirement_audit_missing=requirement_audit.missing,
            structured_stop_violation=structured_stop_violation,
        )
        self.ctx.store.close_session(
            session_id=session_id,
            status=session_status,
            metadata={
                "hook": "Stop",
                "challenge_ok": challenge_ok,
                "challenge_coverage_missing": missing_challenge_coverage,
                "invariant_ok": invariant_ok,
                "requirement_audit_ok": (
                    None if requirement_audit.details is None else requirement_audit.details["ok"]
                ),
                "requirement_audit_missing": requirement_audit.missing,
                "requirement_audit_gap": requirement_audit.gap,
                "required_requirement_ids": required_requirement_ids,
                "required_requirement_ids_source": requirement_ids_source,
                "structured_stop_violation": structured_stop_violation,
            },
        )

        return self._response(
            hook="Stop",
            session_id=session_id,
            warnings=warnings,
            challenge_report=None if challenge_report is None else challenge_report.to_dict(),
            challenge_coverage_missing=missing_challenge_coverage,
            invariant_report=None if invariant_report is None else invariant_report.to_dict(),
            requirement_audit_report=requirement_audit.report,
            required_requirement_ids=required_requirement_ids,
            requirement_audit_missing=requirement_audit.missing,
            requirement_audit_gap=requirement_audit.gap,
            structured_stop_violation=structured_stop_violation,
            recommend_revert=recommend_revert,
            proceed=not recommend_revert,
        )

    def dispatch(self, event_name: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        event_name = self.adapter.normalize(event_name, None).name
        if event_name == "session_start":
            return self.on_session_start(payload)
        if event_name == "pre_tool_use":
            return self.on_pre_tool_use(payload)
        if event_name == "post_tool_use":
            return self.on_post_tool_use(payload)
        if event_name == "stop":
            return self.on_stop(payload)
        raise ValueError(f"Unknown hook event: {event_name}")

    def _record_event(
        self,
        session_id: str,
        hook: str,
        payload: Mapping[str, Any],
        *,
        tool_name: str | None = None,
        status: str | None = None,
    ) -> None:
        self._ensure_session_started(session_id=session_id, hook=hook)
        self.ctx.store.record_event(
            session_id=session_id,
            hook=hook,
            payload=dict(payload),
            tool_name=tool_name,
            status=status,
        )

    def _response(self, *, hook: str, session_id: str, warnings: list[str], **extra: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "hook": hook,
            "session_id": session_id,
            "mode": self.ctx.genome.hooks.mode,
            "warnings": warnings,
            "config": {
                "genome_path": str(self.ctx.genome_path),
                "db_path": str(self.ctx.db_path),
            },
            **extra,
        }

    def _ensure_session_started(self, *, session_id: str, hook: str) -> None:
        self.ctx.store.ensure_session_start(
            session_id=session_id,
            status="running",
            genome_path=self.ctx.genome.source_path,
            metadata={"hook": hook, "auto_started": hook != "SessionStart"},
        )

    def _session_start_repomap(
        self,
        *,
        session_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        repomap_cfg = self.ctx.genome.repomap
        if not (repomap_cfg.enabled and repomap_cfg.run_on_session_start):
            return None

        focus_files = _as_string_list(payload.get("target_files"))
        try:
            from .repomap import run_repomap

            result = run_repomap(
                root=self.ctx.root,
                repomap_config=repomap_cfg,
                focus_files=focus_files or None,
                session_id=session_id,
                timeout_ms=repomap_cfg.session_start_timeout_ms,
            )
        except Exception as exc:  # noqa: BLE001
            summary = {
                "ok": False,
                "artifact_path": None,
                "method": "none",
                "scope": list(repomap_cfg.watch_paths),
                "stats": {
                    "files_parsed": 0,
                    "symbols_found": 0,
                    "graph_edges": 0,
                    "byte_count": 0,
                },
                "top_ranked_files": [],
                "error": {"code": "internal_error", "message": str(exc)},
                "warning": "Repo-map generation failed during session start (non-blocking).",
            }
            self._record_event(
                session_id,
                "RepoMap",
                {
                    "trigger": "SessionStart",
                    "ok": False,
                    "error": summary["error"],
                    "scope": summary["scope"],
                },
                status="error",
            )
            return summary

        artifact = result.artifact
        top_ranked_files = [entry.path for entry in artifact.ranking[:5]]
        summary = {
            "ok": bool(result.ok),
            "artifact_path": result.artifact_path,
            "method": str(artifact.provenance.get("method", "none")),
            "scope": list(artifact.provenance.get("scope", [])),
            "stats": dict(artifact.stats),
            "top_ranked_files": top_ranked_files,
        }
        event_payload: dict[str, Any] = {
            "trigger": "SessionStart",
            "ok": bool(result.ok),
            "artifact_path": result.artifact_path,
            "method": summary["method"],
            "scope": summary["scope"],
            "stats": summary["stats"],
            "top_ranked_files": top_ranked_files,
        }
        if not result.ok and artifact.error:
            error = {
                "code": str(artifact.error.get("code", "internal_error")),
                "message": str(artifact.error.get("message", "Repo-map generation failed")),
            }
            summary["error"] = error
            summary["warning"] = f"Repo-map warning: {error['message']}"
            event_payload["error"] = error

        self._record_event(
            session_id,
            "RepoMap",
            event_payload,
            status="ok" if result.ok else "error",
        )
        return summary

    @staticmethod
    def _graveyard_explainability_warnings(matches: list[dict[str, Any]]) -> list[str]:
        if not matches:
            return []
        top = matches[0]
        summary = str(top.get("summary") or "").strip()
        score = top.get("score")
        semantic_score = top.get("semantic_score")
        keyword_overlap = _as_string_list(top.get("keyword_overlap"))
        file_overlap = _as_string_list(top.get("file_overlap"))
        parts = ["Top graveyard match"]
        if summary:
            parts.append(f"summary='{summary[:120]}'")
        if isinstance(score, (int, float)):
            parts.append(f"score={float(score):.3f}")
        if isinstance(semantic_score, (int, float)):
            parts.append(f"semantic={float(semantic_score):.3f}")
        if keyword_overlap:
            parts.append("keyword_overlap=" + ",".join(keyword_overlap[:5]))
        if file_overlap:
            parts.append("file_overlap=" + ",".join(file_overlap[:3]))
        return ["; ".join(parts)]

    @staticmethod
    def _session_id(payload: Mapping[str, Any]) -> str:
        raw = payload.get("session_id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return f"sess-{uuid4().hex[:12]}"

    @staticmethod
    def _extract_required_requirement_ids(payload: Mapping[str, Any]) -> list[str]:
        direct = _as_string_list(payload.get("required_requirement_ids"))
        if direct:
            return _unique_list(direct)
        contract = payload.get("task_contract")
        if isinstance(contract, Mapping):
            contract_ids = _as_string_list(contract.get("required_requirement_ids")) or _as_string_list(
                contract.get("required_ids")
            )
            if contract_ids:
                return _unique_list(contract_ids)
        return []

    def _session_required_requirement_ids(self, session_id: str) -> list[str]:
        with self.ctx.store.connection() as conn:
            row = conn.execute(
                "SELECT metadata_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return []
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, ValueError):
            return []
        if not isinstance(metadata, dict):
            return []
        return _unique_list(_as_string_list(metadata.get("required_requirement_ids")))

    def _session_witness_context(self, session_id: str) -> dict[str, list[str]]:
        commands: list[str] = []
        tools: list[str] = []
        with self.ctx.store.connection() as conn:
            rows = conn.execute(
                """
                SELECT tool_name, payload_json
                FROM events
                WHERE session_id = ?
                  AND hook IN ('PreToolUse', 'PostToolUse')
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        for row in rows:
            tool = str(row["tool_name"] or "").strip()
            if tool:
                tools.append(tool)
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, ValueError):
                continue
            if not isinstance(payload, dict):
                continue
            commands.extend(self._event_command_candidates(payload))

        return {"commands": _unique_list(commands), "tools": _unique_list(tools)}

    @staticmethod
    def _event_command_candidates(payload: Mapping[str, Any]) -> list[str]:
        commands: list[str] = []
        for key in ("command", "cmd"):
            commands.extend(_as_string_list(payload.get(key)))
        for container_key in ("input", "tool_input"):
            nested = payload.get(container_key)
            if isinstance(nested, Mapping):
                for key in ("command", "cmd"):
                    commands.extend(_as_string_list(nested.get(key)))
        return _unique_list(commands)


def _resolve_adapter(adapter_name: str | None) -> EventAdapter:
    token = str(adapter_name or "claude").strip().lower()
    if token in {"aider", "aider_adapter"}:
        return AiderAdapter()
    return ClaudeCodeAdapter()

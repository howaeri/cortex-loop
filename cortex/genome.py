from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .utils import _as_bool

GENOME_SCHEMA_VERSION = "cortex_toml_v1"


@dataclass(slots=True)
class ProjectConfig:
    name: str = "unknown-project"
    type: str = "generic"
    root: str = "."
@dataclass(slots=True)
class InvariantGraduationConfig:
    enabled: bool = True
    target_dir: str = "tests/invariants/graduated"
@dataclass(slots=True)
class InvariantsConfig:
    suite_paths: list[str] = field(default_factory=list)
    pytest_bin: str = "pytest"
    run_on_stop: bool = True
    execution_mode: str = "host"
    container_engine: str = "docker"
    container_image: str = "python:3.11-slim"
    container_workdir: str = "/workspace"
    graduation: InvariantGraduationConfig = field(default_factory=InvariantGraduationConfig)
@dataclass(slots=True)
class ChallengesConfig:
    active_categories: list[str] = field(default_factory=lambda: ["null_inputs", "boundary_values", "error_handling", "graveyard_regression"])
    custom_paths: list[str] = field(default_factory=list)
    require_coverage: bool = True
@dataclass(slots=True)
class GraveyardConfig:
    enabled: bool = True
    max_matches: int = 5
    similarity_threshold: float = 0.35
    min_keyword_overlap: int = 1
@dataclass(slots=True)
class StabilityThresholds:
    warn_churn_count: int = 8
    high_churn_count: int = 15
@dataclass(slots=True)
class FoundationConfig:
    enabled: bool = True
    watch_paths: list[str] = field(default_factory=lambda: ["src"])
    ignored_dirs: list[str] = field(default_factory=lambda: ["node_modules", "dist", "build", ".git", "__pycache__"])
    stability_thresholds: StabilityThresholds = field(default_factory=StabilityThresholds)
    churn_window_commits: int = 200
@dataclass(slots=True)
class RepomapConfig:
    enabled: bool = False
    run_on_session_start: bool = False
    prefer_ast_graph: bool = True
    watch_paths: list[str] = field(default_factory=lambda: ["src"])
    ignored_dirs: list[str] = field(default_factory=lambda: ["node_modules", "dist", "build", ".git", ".cortex", "__pycache__"])
    max_ranked_files: int = 20
    max_text_bytes: int = 8192
    artifact_path: str = ".cortex/artifacts/repomap/latest.json"
    non_blocking: bool = True
    session_start_timeout_ms: int = 2500
@dataclass(slots=True)
class HooksConfig:
    mode: str = "advisory"
    fail_on_missing_challenge_coverage: bool = False
    recommend_revert_on_invariant_failure: bool = True
    require_requirement_audit: bool = False
    fail_on_requirement_audit_gap: bool = False
    require_evidence_for_passed_requirement: bool = True
    require_structured_stop_payload: bool = False
    allow_message_stop_fallback: bool = False
@dataclass(slots=True)
class MetricsConfig:
    enabled: bool = True
    track: list[str] = field(default_factory=lambda: ["human_oversight_minutes", "interrupt_count", "escaped_defects", "completion_minutes", "foundation_quality"])
@dataclass(slots=True)
class CortexGenome:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    invariants: InvariantsConfig = field(default_factory=InvariantsConfig)
    challenges: ChallengesConfig = field(default_factory=ChallengesConfig)
    graveyard: GraveyardConfig = field(default_factory=GraveyardConfig)
    foundation: FoundationConfig = field(default_factory=FoundationConfig)
    repomap: RepomapConfig = field(default_factory=RepomapConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    source_path: str | None = None
    parse_error: str | None = None
    def to_dict(self) -> dict[str, Any]: return asdict(self)


def load_genome(path: str | Path | None = None) -> CortexGenome:
    config_path = Path(path) if path is not None else Path("cortex.toml")
    if not config_path.exists():
        return CortexGenome(source_path=str(config_path))
    try:
        with config_path.open("rb") as fh:
            raw = tomllib.load(fh)
        if not isinstance(raw, dict):
            raise ValueError("Top-level TOML must be a table")
    except Exception as exc:  # noqa: BLE001
        return CortexGenome(source_path=str(config_path), parse_error=str(exc))
    return CortexGenome(
        project=_load_project(raw.get("project", {})),
        invariants=_load_invariants(raw.get("invariants", {})),
        challenges=_load_challenges(raw.get("challenges", {})),
        graveyard=_load_graveyard(raw.get("graveyard", {})),
        foundation=_load_foundation(raw.get("foundation", {})),
        repomap=_load_repomap(raw.get("repomap", {})),
        hooks=_load_hooks(raw.get("hooks", {})),
        metrics=_load_metrics(raw.get("metrics", {})),
        source_path=str(config_path),
    )


def _load_project(data: Any) -> ProjectConfig:
    d, x = _as_dict(data), ProjectConfig()
    return ProjectConfig(name=str(d.get("name", x.name)), type=str(d.get("type", x.type)), root=str(d.get("root", x.root)))
def _load_invariants(data: Any) -> InvariantsConfig:
    d, x, g = _as_dict(data), InvariantsConfig(), _as_dict(_as_dict(data).get("graduation", {}))
    gd = InvariantGraduationConfig()
    execution_mode = str(d.get("execution_mode", x.execution_mode)).strip().lower()
    if execution_mode not in {"host", "container"}:
        execution_mode = x.execution_mode
    return InvariantsConfig(
        suite_paths=[str(v) for v in _as_list(d.get("suite_paths"), x.suite_paths)],
        pytest_bin=str(d.get("pytest_bin", x.pytest_bin)),
        run_on_stop=_as_bool(d.get("run_on_stop"), x.run_on_stop),
        execution_mode=execution_mode,
        container_engine=str(d.get("container_engine", x.container_engine)),
        container_image=str(d.get("container_image", x.container_image)),
        container_workdir=str(d.get("container_workdir", x.container_workdir)),
        graduation=InvariantGraduationConfig(
            enabled=_as_bool(g.get("enabled"), gd.enabled),
            target_dir=str(g.get("target_dir", gd.target_dir)),
        ),
    )
def _load_challenges(data: Any) -> ChallengesConfig:
    d, x = _as_dict(data), ChallengesConfig()
    return ChallengesConfig(active_categories=[str(v) for v in _as_list(d.get("active_categories"), x.active_categories)] or list(x.active_categories), custom_paths=[str(v) for v in _as_list(d.get("custom_paths"), x.custom_paths)], require_coverage=_as_bool(d.get("require_coverage"), x.require_coverage))
def _load_graveyard(data: Any) -> GraveyardConfig:
    d, x = _as_dict(data), GraveyardConfig()
    return GraveyardConfig(enabled=_as_bool(d.get("enabled"), x.enabled), max_matches=_as_int(d.get("max_matches"), x.max_matches), similarity_threshold=_as_float(d.get("similarity_threshold"), x.similarity_threshold), min_keyword_overlap=_as_int(d.get("min_keyword_overlap"), x.min_keyword_overlap))
def _load_foundation(data: Any) -> FoundationConfig:
    d, x, td = _as_dict(data), FoundationConfig(), StabilityThresholds()
    t = _as_dict(d.get("stability_thresholds", {}))
    return FoundationConfig(enabled=_as_bool(d.get("enabled"), x.enabled), watch_paths=[str(v) for v in _as_list(d.get("watch_paths"), x.watch_paths)], ignored_dirs=[str(v) for v in _as_list(d.get("ignored_dirs"), x.ignored_dirs)], stability_thresholds=StabilityThresholds(warn_churn_count=_as_int(t.get("warn_churn_count"), td.warn_churn_count), high_churn_count=_as_int(t.get("high_churn_count"), td.high_churn_count)), churn_window_commits=_as_int(d.get("churn_window_commits"), x.churn_window_commits))
def _load_repomap(data: Any) -> RepomapConfig:
    d, x = _as_dict(data), RepomapConfig()
    return RepomapConfig(enabled=_as_bool(d.get("enabled"), x.enabled), run_on_session_start=_as_bool(d.get("run_on_session_start"), x.run_on_session_start), prefer_ast_graph=_as_bool(d.get("prefer_ast_graph"), x.prefer_ast_graph), watch_paths=[str(v) for v in _as_list(d.get("watch_paths"), x.watch_paths)], ignored_dirs=[str(v) for v in _as_list(d.get("ignored_dirs"), x.ignored_dirs)], max_ranked_files=_as_int(d.get("max_ranked_files"), x.max_ranked_files), max_text_bytes=_as_int(d.get("max_text_bytes"), x.max_text_bytes), artifact_path=str(d.get("artifact_path", x.artifact_path)), non_blocking=_as_bool(d.get("non_blocking"), x.non_blocking), session_start_timeout_ms=_as_int(d.get("session_start_timeout_ms"), x.session_start_timeout_ms))
def _load_hooks(data: Any) -> HooksConfig:
    d, x = _as_dict(data), HooksConfig()
    return HooksConfig(
        mode=str(d.get("mode", x.mode)),
        fail_on_missing_challenge_coverage=_as_bool(
            d.get("fail_on_missing_challenge_coverage"), x.fail_on_missing_challenge_coverage
        ),
        recommend_revert_on_invariant_failure=_as_bool(
            d.get("recommend_revert_on_invariant_failure"), x.recommend_revert_on_invariant_failure
        ),
        require_requirement_audit=_as_bool(
            d.get("require_requirement_audit"), x.require_requirement_audit
        ),
        fail_on_requirement_audit_gap=_as_bool(
            d.get("fail_on_requirement_audit_gap"), x.fail_on_requirement_audit_gap
        ),
        require_evidence_for_passed_requirement=_as_bool(
            d.get("require_evidence_for_passed_requirement"), x.require_evidence_for_passed_requirement
        ),
        require_structured_stop_payload=_as_bool(
            d.get("require_structured_stop_payload"), x.require_structured_stop_payload
        ),
        allow_message_stop_fallback=_as_bool(
            d.get("allow_message_stop_fallback"), x.allow_message_stop_fallback
        ),
    )
def _load_metrics(data: Any) -> MetricsConfig:
    d, x = _as_dict(data), MetricsConfig()
    return MetricsConfig(enabled=_as_bool(d.get("enabled"), x.enabled), track=[str(v) for v in _as_list(d.get("track"), x.track)])


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
def _as_list(value: Any, default: list[Any]) -> list[Any]:
    return value if isinstance(value, list) else list(default)
def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
def collect_active_metric_names(genome: CortexGenome) -> Iterable[str]:
    return genome.metrics.track if genome.metrics.enabled else []

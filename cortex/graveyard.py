from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from .genome import GraveyardConfig
from .store import SQLiteStore


_WORD_RE = re.compile(r"[A-Za-z0-9_./-]+")
_SYNONYM_CANONICAL = {
    "redis": "cache",
    "caching": "cache",
    "latency": "timeout",
    "slow": "timeout",
    "slowness": "timeout",
    "crash": "fail",
    "crashed": "fail",
    "failure": "fail",
    "failed": "fail",
    "error": "fail",
    "errors": "fail",
    "exception": "fail",
    "exceptions": "fail",
    "connection": "connect",
    "connections": "connect",
}


@dataclass(slots=True)
class GraveyardMatch:
    entry_id: int
    score: float
    summary: str
    reason: str
    files: list[str]
    keyword_overlap: list[str]
    file_overlap: list[str]
    semantic_score: float
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "score": round(self.score, 3),
            "summary": self.summary,
            "reason": self.reason,
            "files": self.files,
            "keyword_overlap": self.keyword_overlap,
            "file_overlap": self.file_overlap,
            "semantic_score": round(self.semantic_score, 3),
            "created_at": self.created_at,
        }


class Graveyard:
    def __init__(self, store: SQLiteStore, config: GraveyardConfig) -> None:
        self.store = store
        self.config = config

    def record_failure(
        self,
        session_id: str | None,
        summary: str,
        reason: str,
        files: Iterable[str] = (),
    ) -> None:
        if not self.config.enabled:
            return
        file_list = [str(path) for path in files]
        keywords = sorted(self._keywords(summary) | self._keywords(reason))
        self.store.insert_graveyard(
            session_id=session_id,
            summary=summary,
            reason=reason,
            files=file_list,
            keywords=keywords,
        )

    def find_similar(
        self,
        summary: str,
        files: Iterable[str] = (),
        *,
        max_matches: int | None = None,
    ) -> list[GraveyardMatch]:
        if not self.config.enabled:
            return []

        query_keywords = self._keywords(summary)
        query_tokens = self._tokenize(summary)
        query_token_set = set(query_tokens)
        query_files = {self._norm_path(p) for p in files if p}
        if not query_tokens and not query_files:
            return []

        corpus_entries = self.store.list_graveyard(limit=200)
        entries = self._load_candidate_entries(query_tokens=query_tokens)
        idf_source = corpus_entries or entries
        df = Counter(token for entry in idf_source for token in {str(v) for v in entry.get("keywords", [])})
        query_idf = {token: math.log((len(idf_source) + 1) / (df.get(token, 0) + 1)) + 1.0 for token in query_keywords}
        query_weight = sum(query_idf.values()) or 1.0
        scored: list[GraveyardMatch] = []
        for entry in entries:
            entry_keywords = {str(k) for k in entry.get("keywords", [])}
            entry_tokens = self._tokenize(f"{entry.get('summary', '')} {entry.get('reason', '')}")
            entry_files = {self._norm_path(p) for p in entry.get("files", [])}
            keyword_overlap = sorted(query_keywords & entry_keywords)
            file_overlap = sorted(query_files & entry_files)

            keyword_score = sum(query_idf[token] for token in keyword_overlap) / query_weight
            file_score = len(file_overlap) / max(1, len(query_files)) if query_files else 0.0
            semantic_score = self._token_jaccard(query_token_set, set(entry_tokens))
            if (
                len(keyword_overlap) < self.config.min_keyword_overlap
                and not file_overlap
                and semantic_score < self.config.similarity_threshold
            ):
                continue

            score = (keyword_score * 0.45) + (file_score * 0.25) + (semantic_score * 0.30)
            if score < self.config.similarity_threshold:
                continue
            scored.append(
                GraveyardMatch(
                    entry_id=int(entry["id"]),
                    score=score,
                    summary=str(entry["summary"]),
                    reason=str(entry["reason"]),
                    files=list(entry["files"]),
                    keyword_overlap=keyword_overlap,
                    file_overlap=file_overlap,
                    semantic_score=semantic_score,
                    created_at=str(entry["created_at"]),
                )
            )

        scored.sort(key=lambda m: (m.score, m.entry_id), reverse=True)
        return scored[: (max_matches or self.config.max_matches)]

    def _load_candidate_entries(self, *, query_tokens: list[str]) -> list[dict[str, object]]:
        if not query_tokens:
            return self.store.list_graveyard(limit=200)
        candidates = self.store.list_graveyard_fts_candidates(tokens=query_tokens, limit=200, candidate_limit=80)
        if not candidates:
            return self.store.list_graveyard(limit=200)
        return candidates

    @staticmethod
    def _keywords(text: str) -> set[str]:
        return set(Graveyard._tokenize(text))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        for raw in _WORD_RE.findall(text):
            token = Graveyard._normalize_token(raw)
            if token:
                tokens.append(token)
        return tokens

    @staticmethod
    def _normalize_token(token: str) -> str:
        value = token.lower().strip("._/-")
        if len(value) <= 2:
            return ""
        if value.endswith("ies") and len(value) > 4:
            value = value[:-3] + "y"
        elif value.endswith("ing") and len(value) > 5:
            value = value[:-3]
        elif value.endswith("ed") and len(value) > 4:
            value = value[:-2]
        elif value.endswith("s") and len(value) > 3:
            value = value[:-1]
        return _SYNONYM_CANONICAL.get(value, value)

    @staticmethod
    def _token_jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    @staticmethod
    def _norm_path(path: str) -> str:
        parts = [p for p in str(PurePosixPath(path)).split("/") if p not in {"", "."}]
        return "/".join(parts)

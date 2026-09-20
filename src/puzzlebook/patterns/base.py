"""Pattern detection primitives: matches, detectors and the registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

import pandas as pd


@dataclass
class PatternMatch:
    """A single detected pattern ending at ``end_idx`` (inclusive).

    ``end_idx`` is the "puzzle moment": the last bar that may be shown to the
    reader. Bars after ``end_idx`` must never be rendered (no look-ahead).
    """

    name: str
    direction: str  # "bullish" | "bearish" | "neutral"
    end_idx: int
    start_idx: int
    symbol: str = ""
    score: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def bar_count(self) -> int:
        return self.end_idx - self.start_idx + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "end_idx": self.end_idx,
            "start_idx": self.start_idx,
            "symbol": self.symbol,
            "score": self.score,
            "meta": self.meta,
        }


class PatternDetector(ABC):
    """Base class for every detector. Subclass + :func:`register` to extend."""

    name: str = "base"
    direction: str = "neutral"
    kind: str = "generic"

    @abstractmethod
    def detect(
        self, df: pd.DataFrame, cfg: Mapping[str, Any]
    ) -> List[PatternMatch]:
        """Return every occurrence of this pattern in ``df``."""


_REGISTRY: Dict[str, PatternDetector] = {}


def register(detector: PatternDetector) -> PatternDetector:
    """Register a detector instance under its ``name``."""
    _REGISTRY[detector.name] = detector
    return detector


def get(name: str) -> PatternDetector:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown detector {name!r}. Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def available() -> List[str]:
    return sorted(_REGISTRY)


def build_detectors(cfg: Mapping[str, Any]) -> List[PatternDetector]:
    """Instantiate the detectors enabled in config, in a stable order."""
    patterns = cfg["patterns"]
    names: List[str] = []
    if patterns["candlestick"]["enabled"]:
        names += list(patterns["candlestick"]["names"])
    if patterns["chart"]["enabled"]:
        names += list(patterns["chart"]["names"])
    detectors: List[PatternDetector] = []
    for name in names:
        detector = _REGISTRY.get(name)
        if detector is not None:
            detectors.append(detector)
    return detectors

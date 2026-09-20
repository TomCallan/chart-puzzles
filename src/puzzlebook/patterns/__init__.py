"""Pattern detection package.

Importing this package registers every built-in detector. Add a new pattern
by creating a detector class, registering it, and listing its name in
``config.yaml`` under ``patterns.candlestick.names`` or ``patterns.chart.names``.
"""

from __future__ import annotations

from .base import (  # noqa: F401
    PatternDetector,
    PatternMatch,
    available,
    build_detectors,
    get,
    register,
)
from . import candlestick  # noqa: F401  (registers candlestick detectors)
from . import chart  # noqa: F401  (registers chart detectors)
from .scoring import cleanliness_score, dedupe, score_matches  # noqa: F401

__all__ = [
    "PatternDetector",
    "PatternMatch",
    "available",
    "build_detectors",
    "get",
    "register",
    "cleanliness_score",
    "score_matches",
    "dedupe",
]

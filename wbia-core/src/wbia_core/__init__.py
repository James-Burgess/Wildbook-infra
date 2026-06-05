"""Core animal identification algorithm — extracted from Wildbook IA."""

from wbia_core.config import (
    HotSpotterConfig,
    IdentificationConfig,
    MiewIdConfig,
    SiftConfig,
)
from wbia_core.data import AnnotatedImage, FeatureSet, Match, ScoredMatch
from wbia_core.pipeline import identify

__all__ = [
    # Config
    "IdentificationConfig",
    "HotSpotterConfig",
    "MiewIdConfig",
    "SiftConfig",
    # Data
    "FeatureSet",
    "AnnotatedImage",
    "Match",
    "ScoredMatch",
    # Pipeline
    "identify",
]

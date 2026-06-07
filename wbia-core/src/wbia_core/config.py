"""Pydantic models for algorithm configuration."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SiftConfig(BaseModel):
    scale: list[float] = Field(
        default_factory=lambda: [1.0, 4.0, 8.0],
        description="Scales for Hessian-affine detection",
    )
    ori_hist_bins: int = Field(default=36, ge=8, le=360)
    ori_hist_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class HotSpotterConfig(BaseModel):
    knn: int = Field(default=4, ge=1, description="Number of nearest neighbors")
    kpad: int = Field(
        default=0, ge=0, description="Extra K columns for self-filtering buffer"
    )
    kpad_policy: Literal["fixed", "dynamic"] = Field(
        default="fixed",
        description="'fixed' uses kpad value; 'dynamic' computes from impossible annots",
    )
    score_method: Literal["csum", "nsum", "csum_wbia", "nsum_wbia", "sumamech"] = Field(
        default="csum",
        description=(
            "Simple: 'csum' (per-annot sum), 'nsum' (per-annot avg). "
            "WBIA: 'nsum_wbia' (fmech), 'csum_wbia' (max-per-name), 'sumamech'"
        ),
    )
    prescore_method: Literal["csum", "nsum", "csum_wbia", "nsum_wbia", "sumamech"] = (
        Field(default="csum")
    )
    normalizer_rule: Literal["last", "name"] = Field(
        default="last",
        description="'last' uses farthest neighbour; 'name' picks from different name ID",
    )
    sv_on: bool = Field(default=True, description="Enable spatial verification")
    num_return: int = Field(default=10, ge=1)
    ratio_thresh: Optional[float] = Field(default=None, gt=0.0)
    lnbnn_ratio: float = Field(default=1.0, gt=0.0)
    fg_on: bool = Field(default=True)

    # Additional WBIA filters (defaults match WBIA)
    bar_l2_on: bool = Field(default=False)
    const_on: bool = Field(default=False)

    # FLANN index parameters (matching WBIA defaults)
    flann_algorithm: str = Field(default="kdtree")
    flann_trees: int = Field(default=4)
    flann_random_seed: int = Field(default=42)
    flann_checks: int = Field(default=1028)
    flann_cores: int = Field(default=0)


class MiewIdConfig(BaseModel):
    enabled: bool = Field(default=False)


class IdentificationConfig(BaseModel):
    pipeline: Literal["HotSpotter", "MiewId", "CurvRank", "Deepsqueak"] = Field(
        default="HotSpotter"
    )
    hotspotter: HotSpotterConfig = Field(default_factory=HotSpotterConfig)
    miewid: MiewIdConfig = Field(default_factory=MiewIdConfig)

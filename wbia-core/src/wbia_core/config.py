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
    score_method: Literal["nsum", "csum"] = Field(default="csum")
    prescore_method: Literal["nsum", "csum"] = Field(default="csum")
    sv_on: bool = Field(default=True, description="Enable spatial verification")
    num_return: int = Field(default=10, ge=1)
    ratio_thresh: Optional[float] = Field(default=None, gt=0.0)
    lnbnn_ratio: float = Field(default=1.0, gt=0.0)
    fg_on: bool = Field(default=True)

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

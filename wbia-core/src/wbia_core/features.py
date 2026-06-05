"""Feature extraction via pyhesaff SIFT (optional) with OpenCV fallback."""

from __future__ import annotations

import warnings

import numpy as np

from wbia_core.config import SiftConfig
from wbia_core.data import FeatureSet
from wbia_core.exceptions import NotInstalledError


def _to_hesaff_kwargs(config: SiftConfig, default_params: dict | None = None) -> dict:
    """Merge SiftConfig overrides into pyhesaff default parameters."""
    kwargs = dict(default_params) if default_params else {}
    if config.scale is not None and len(config.scale) > 0:
        kwargs["numberOfScales"] = len(config.scale)
    kwargs["ori_maxima_thresh"] = config.ori_hist_threshold
    return kwargs


def extract_features(
    image: np.ndarray, config: SiftConfig = SiftConfig()
) -> FeatureSet:
    """Extract Hessian-affine SIFT features from *image*.

    Uses ``wbia-pyhesaff`` when available, otherwise falls back to
    OpenCV ``cv2.SIFT_create()``.

    Args:
        image: [H, W] or [H, W, 3] uint8.
        config: SIFT extraction parameters.

    Returns:
        FeatureSet with *N* keypoints and descriptors.

    Raises:
        NotInstalledError: neither pyhesaff nor OpenCV SIFT is available.
    """
    try:
        import pyhesaff as _h

        hesaff_kwargs = _to_hesaff_kwargs(config, _h.get_hesaff_default_params())
        keypoints, descriptors = _h.detect_feats_in_image(image, **hesaff_kwargs)
        return FeatureSet(keypoints=keypoints, descriptors=descriptors)
    except ImportError:
        pass

    try:
        import cv2
    except ImportError:
        raise NotInstalledError(
            "No feature extractor available.  Install opencv-python-headless "
            "or wbia-pyhesaff (pip install wbia-core[features])"
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    nfeatures = int(config.scale[-1] * 1000) if config.scale else 4000
    sift = cv2.SIFT_create(nfeatures, 3)
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    if keypoints is None:
        return FeatureSet(
            keypoints=np.empty((0, 4), dtype=np.float32),
            descriptors=np.empty((0, 128), dtype=np.uint8),
        )

    pts = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    scales = np.array([kp.size for kp in keypoints], dtype=np.float32)
    angles = np.array([kp.angle for kp in keypoints], dtype=np.float32)
    half = scales / 2.0
    hs2 = half * half
    kp_arr = np.column_stack([pts, hs2, np.zeros_like(hs2), hs2, angles])
    return FeatureSet(keypoints=kp_arr, descriptors=descriptors.astype(np.uint8))

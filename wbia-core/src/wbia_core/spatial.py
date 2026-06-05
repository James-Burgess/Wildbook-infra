"""Spatial verification via RANSAC homography (OpenCV).

Uses exact per-feature correspondences threaded through from the
scoring stage (``ScoredMatch.correspondences``) to build the
keypoint pairs for ``cv2.findHomography``.
"""

from __future__ import annotations

import cv2
import numpy as np

from wbia_core.data import AnnotatedImage, FeatureSet, ScoredMatch


def spatial_verify(
    matches: list[ScoredMatch],
    query_features: FeatureSet,
    database: list[AnnotatedImage],
    ransac_thresh: float = 3.0,
    min_inliers: int = 3,
) -> list[ScoredMatch]:
    """Run spatial verification (RANSAC homography) on each candidate.

    Only candidates with ``num_matches >= min_inliers`` are verified.
    The homography is computed from the exact per-feature correspondences
    stored in ``ScoredMatch.correspondences`` as ``(qfx, dfx)`` pairs.

    Args:
        matches: scored candidates from :func:`scoring.score_matches`.
        query_features: query image feature set.
        database: annotations in index order.
        ransac_thresh: RANSAC reprojection threshold (pixels).
        min_inliers: minimum inliers to accept homography.

    Returns:
        Updated list with ``sv_inliers`` and ``sv_homography`` populated.
    """
    q_kp = query_features.keypoints  # [N, 6]

    for sm in matches:
        if len(sm.correspondences) < min_inliers:
            continue

        ann_idx = next(
            i for i, a in enumerate(database) if a.annot_uuid == sm.annot_uuid
        )
        db_kp = database[ann_idx].features.keypoints  # [M, 6]

        q_pts = []
        db_pts = []

        for qfx, dfx in sm.correspondences:
            if qfx < q_kp.shape[0] and dfx < db_kp.shape[0]:
                q_pts.append(q_kp[qfx, :2])
                db_pts.append(db_kp[dfx, :2])

        if len(q_pts) < 4:
            continue

        q_pts = np.array(q_pts, dtype=np.float32)
        db_pts = np.array(db_pts, dtype=np.float32)

        H, mask = cv2.findHomography(q_pts, db_pts, cv2.RANSAC, ransac_thresh)
        if H is not None and mask is not None:
            inliers = int(mask.sum())
            if inliers >= min_inliers:
                sm.sv_inliers = inliers
                sm.sv_homography = H
                # Boost score proportional to inlier ratio
                sm.score = sm.score * (1.0 + 0.5 * inliers / len(sm.correspondences))

    return matches

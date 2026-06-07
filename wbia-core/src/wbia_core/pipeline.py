"""Stateless identification pipeline — top-level :func:`identify`.

Matches WBIA's global-index ``vsmany`` pipeline:

* A **single** FLANN index over ALL database descriptors (including
  the query), matching WBIA's ``NeighborIndex``  behaviour.
* ``K+Kpad`` voting columns + ``Knorm`` normaliser column; self /
  same-name matches are filtered from the voting columns only
  (WBIA's ``baseline_neighbor_filter``).
* Maintains the same data ordering as WBIA's ``daid_list`` so that
  the FLANN KD-tree structure is reproducible.
"""

from __future__ import annotations

import numpy as np

from wbia_core.config import IdentificationConfig
from wbia_core.data import AnnotatedImage, FeatureSet, Match, ScoredMatch
from wbia_core.knn import build_global_index, exact_knn, query_index
from wbia_core.scoring import per_feature_fg, score_matches
from wbia_core.spatial import spatial_verify


def identify(
    query_annot_index: int,
    database: list[AnnotatedImage],
    config: IdentificationConfig = IdentificationConfig(),
) -> list[ScoredMatch]:
    """Run the identification pipeline for one query against *database*.

    A single global FLANN index is built over **all** descriptors
    (including the query), matching WBIA.  The ``K+Kpad+Knorm``
    nearest neighbours are fetched; self / same-name matches are
    filtered from the voting columns only (the ``Knorm`` normaliser
    column is not filtered).

    Args:
        query_annot_index: index of the query annotation in *database*.
        database: all candidate annotations (may include the query).
        config: pipeline configuration.

    Returns:
        Top-``config.hotspotter.num_return`` scored matches descending.
    """
    hs = config.hotspotter
    query_features = database[query_annot_index].features

    if config.pipeline != "HotSpotter":
        raise NotImplementedError(
            f"Pipeline {config.pipeline!r} is not yet implemented."
        )

    k = hs.knn
    kpad = hs.kpad
    knorm = 1  # WBIA default
    k_total = k + kpad + knorm  # e.g. 4 + 1 + 1 = 6

    # ---- 1. Build global FLANN index over ALL annotations ----
    # WBIA uses daid_list order → same order as database list
    all_features = [ann.features for ann in database]

    if hs.flann_algorithm == "exact":
        # Exact N-N: concatenate all descriptors, use numpy dot product
        import numpy as _np

        all_descs = _np.concatenate([fs.descriptors for fs in all_features], axis=0)
        n_total = all_descs.shape[0]
        annot_of_desc = _np.empty(n_total, dtype=_np.int32)
        feat_of_desc = _np.empty(n_total, dtype=_np.int32)
        offset = 0
        for i, fs in enumerate(all_features):
            n = len(fs)
            annot_of_desc[offset : offset + n] = i
            feat_of_desc[offset : offset + n] = _np.arange(n, dtype=_np.int32)
            offset += n
        db_feats = FeatureSet(
            keypoints=_np.empty((n_total, 6), dtype=_np.float64),
            descriptors=all_descs,
        )
        raw_dists, raw_labels = exact_knn(query_features, db_feats, k_total)
    else:
        global_index, annot_of_desc, feat_of_desc = build_global_index(
            all_features,
            algorithm=hs.flann_algorithm,
            trees=hs.flann_trees,
            random_seed=hs.flann_random_seed,
        )
        n_total = annot_of_desc.shape[0]

        # ---- 2. Query global index ----
        raw_dists, raw_labels = query_index(
            global_index,
            query_features,
            k_total,
            checks=hs.flann_checks,
            cores=hs.flann_cores,
        )

    # Post-hoc distance normalisation (WBIA VEC_PSEUDO_MAX_DISTANCE_SQRD)
    # WBIA divides raw SSE by 524288, then takes sqrt (sqrd_dist_on=False default).
    max_distance_sqrd = 2.0 * (512.0**2.0)
    dists = (np.maximum(raw_dists, 0.0) / max_distance_sqrd).astype(np.float64)
    dists = np.sqrt(dists)
    labels = raw_labels.astype(np.int64)

    n_qfxs = dists.shape[0]

    # First K+Kpad columns = voting candidates; last column = LNBNN normaliser
    voting_dists_all = dists[:, : k + kpad]  # [M, K+Kpad]
    norm_dists = dists[:, -1:]  # [M, 1]

    # Map every neighbour column back to (annot_idx, feat_idx) in the
    # *original* database order (annot_of_desc already uses that order).
    voting_annot_all = np.full((n_qfxs, k + kpad), -1, dtype=np.int32)
    voting_feat_all = np.full((n_qfxs, k + kpad), -1, dtype=np.int32)
    for j in range(k + kpad):
        col = labels[:, j]
        valid = (col >= 0) & (col < n_total)
        voting_annot_all[valid, j] = annot_of_desc[col[valid]]
        voting_feat_all[valid, j] = feat_of_desc[col[valid]]

    # ---- 3. Baseline-neighbour filter (self + same-name) ----
    # Like WBIA's baseline_neighbor_filter: only the first K+Kpad columns
    # are checked; the normaliser column is NOT filtered.
    qname = database[query_annot_index].name_uuid
    if qname is not None:
        same_name_set = {
            i
            for i, a in enumerate(database)
            if i != query_annot_index and a.name_uuid == qname
        }
    else:
        same_name_set = set()

    invalid = (voting_annot_all == query_annot_index) | np.isin(
        voting_annot_all, list(same_name_set)
    )  # [M, K+Kpad], bool

    # ---- 4. FG weights ----
    if hs.fg_on:
        fg_weights = [per_feature_fg(ann) for ann in database]
        q_fgw = fg_weights[query_annot_index]
    else:
        fg_weights = None
        q_fgw = None

    # ---- 5. WBIA filter chain → flat match list ----
    # WBIA multiplies ALL active filter columns:
    #   weight = lnbnn * bar_l2 * (const) * (fg) * (ratio)
    # bar_l2 = 1 - vdist  is always ON in WBIA's pipeline.
    matches: list[Match] = []
    for qfx in range(n_qfxs):
        for j in range(k + kpad):
            w = float(norm_dists[qfx, 0]) - float(voting_dists_all[qfx, j])
            db_idx = int(voting_annot_all[qfx, j])
            if db_idx < 0 or invalid[qfx, j]:
                continue
            dfx = int(voting_feat_all[qfx, j])
            if dfx < 0:
                continue

            if hs.fg_on and q_fgw is not None:
                w *= np.sqrt(float(q_fgw[qfx]) * float(fg_weights[db_idx][dfx]))

            matches.append(
                Match(
                    qfx=qfx,
                    daid=db_idx,
                    dfx=dfx,
                    dist=w,
                    name_uuid=database[db_idx].name_uuid,
                )
            )

    # ---- 6. Score ----
    scored = score_matches(matches, database, hs.score_method)

    # ---- 7. Spatial verification ----
    if hs.sv_on:
        scored = spatial_verify(scored, query_features, database)

    if hs.sv_on and hs.prescore_method != hs.score_method:
        scored = score_matches(matches, database, hs.score_method)

    return scored[: hs.num_return]

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
from wbia_core.debug_log import (
    stage_dist_norm,
    stage_features,
    stage_filter_counts,
    stage_final,
    stage_global_index,
    stage_lnbnn_weights,
    stage_match_to_annot,
    stage_raw_dists,
    stage_voting_cols,
)


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
    stage_features(database)

    all_features = [ann.features for ann in database]

    if hs.flann_algorithm == "exact":
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

    stage_global_index(all_features, annot_of_desc)
    stage_raw_dists(raw_dists, raw_labels)

    # Post-hoc distance normalisation
    max_distance_sqrd = 2.0 * (512.0**2.0)
    dists = (np.maximum(raw_dists, 0.0) / max_distance_sqrd).astype(np.float64)
    dists = np.sqrt(dists)
    labels_normalised = raw_labels.astype(np.int64)

    stage_dist_norm(dists)

    n_qfxs = dists.shape[0]

    # First K+Kpad columns = voting candidates; last column = normaliser
    voting_dists_all = dists[:, : k + kpad]
    norm_dists = dists[:, -1:]

    # Map neighbour columns back to (annot_idx, feat_idx)
    voting_annot_all = np.full((n_qfxs, k + kpad), -1, dtype=np.int32)
    voting_feat_all = np.full((n_qfxs, k + kpad), -1, dtype=np.int32)
    for j in range(k + kpad):
        col = labels_normalised[:, j]
        valid = (col >= 0) & (col < n_total)
        voting_annot_all[valid, j] = annot_of_desc[col[valid]]
        voting_feat_all[valid, j] = feat_of_desc[col[valid]]

    stage_voting_cols(
        dists, labels_normalised, annot_of_desc, k, kpad, query_annot_index
    )

    # ---- 3. Baseline-neighbour filter ----
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
    )

    stage_filter_counts(
        dists,
        labels_normalised,
        annot_of_desc,
        k,
        kpad,
        query_annot_index,
        same_name_set,
    )

    # ---- 4. FG weights ----
    if hs.fg_on:
        fg_weights = [per_feature_fg(ann) for ann in database]
        q_fgw = fg_weights[query_annot_index]
    else:
        fg_weights = None
        q_fgw = None

    # ---- 5. LNBNN weights → flat match list ----
    matches: list[Match] = []
    lnbnn_weights: list[float] = []
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

            lnbnn_weights.append(w)
            matches.append(
                Match(
                    qfx=qfx,
                    daid=db_idx,
                    dfx=dfx,
                    dist=w,
                    name_uuid=database[db_idx].name_uuid,
                )
            )

    stage_lnbnn_weights(lnbnn_weights)

    # ---- 6. Score ----
    scored = score_matches(matches, database, hs.score_method)

    annot_to_matches: dict[object, tuple[float, int]] = {}
    for m in matches:
        auuid = database[m.daid].annot_uuid
        s, cnt = annot_to_matches.get(auuid, (0.0, 0))
        annot_to_matches[auuid] = (s + m.dist, cnt + 1)
    stage_match_to_annot(annot_to_matches)

    # ---- 7. Spatial verification ----
    if hs.sv_on:
        scored = spatial_verify(scored, query_features, database)

    if hs.sv_on and hs.prescore_method != hs.score_method:
        scored = score_matches(matches, database, hs.score_method)

    result = scored[: hs.num_return]
    stage_final(result)
    return result

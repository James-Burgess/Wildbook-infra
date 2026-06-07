"""Beautiful debug logging for the identification pipeline.

Usage: set the env var ``WBIA_CORE_DEBUG=1`` to enable.
    WBIA_CORE_DEBUG=1 python -m pytest tests/benchmark/...
"""

from __future__ import annotations

import logging
import os

import numpy as np

_logger = logging.getLogger("wbia-core.pipeline")


def _enabled() -> bool:
    return os.environ.get("WBIA_CORE_DEBUG", "0") == "1"


def _setup():
    if not _enabled():
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False


_setup()

SEP = "─" * 72
THIN = "·" * 48


def _pct(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{100.0 * count / total:.1f}%"


def _stats(arr: np.ndarray) -> str:
    a = arr.flatten()
    return (
        f"min={np.min(a):.4f}  max={np.max(a):.4f}  "
        f"μ={np.mean(a):.4f}  σ={np.std(a):.4f}"
    )


# ── Stages ────────────────────────────────────────────────────────────


def stage_features(database: list) -> None:
    if not _enabled():
        return
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 1 — Feature Extraction")
    _logger.debug("%s", SEP)
    for i, ann in enumerate(database):
        fs = ann.features
        tag = "QUERY" if i == 0 else f"  db[{i}]"
        _logger.debug(
            "  %-10s  annot=%s  kp=%5d  desc=%s×%d",
            tag,
            str(ann.annot_uuid)[:8],
            len(fs),
            fs.descriptors.shape,
            fs.descriptors.shape[1],
        )


def stage_global_index(all_features: list, annot_of_desc: np.ndarray) -> None:
    if not _enabled():
        return
    total_n = annot_of_desc.shape[0]
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 2 — Global FLANN Index")
    _logger.debug("%s", SEP)
    _logger.debug("  total descriptors  %d", total_n)
    for i in range(len(all_features)):
        cnt = int((annot_of_desc == i).sum())
        tag = "QUERY" if i == 0 else f"  db[{i}]"
        _logger.debug("  %-10s  desc=%5d  (%s of total)", tag, cnt, _pct(cnt, total_n))


def stage_raw_dists(raw_dists: np.ndarray, raw_labels: np.ndarray) -> None:
    if not _enabled():
        return
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 3 — Raw FLANN Query")
    _logger.debug("%s", SEP)
    _logger.debug(
        "  shape       (M × K) = (%d × %d)", raw_dists.shape[0], raw_dists.shape[1]
    )
    _logger.debug("  distances   %s", _stats(raw_dists))
    valid = (raw_labels >= 0).sum()
    total = raw_labels.size
    _logger.debug("  labels      valid=%d/%d (%s)", valid, total, _pct(valid, total))


def stage_dist_norm(dists: np.ndarray) -> None:
    if not _enabled():
        return
    _logger.debug("")
    _logger.debug("  %s", THIN)
    _logger.debug("  STEP 4 — Distance Normalization  ( / 524288, sqrt )")
    _logger.debug("  %s", THIN)
    _logger.debug("  distances   %s", _stats(dists))


def stage_voting_cols(
    dists: np.ndarray,
    labels: np.ndarray,
    annot_of_desc: np.ndarray,
    k: int,
    kpad: int,
    query_idx: int,
) -> None:
    if not _enabled():
        return
    voting = dists[:, : k + kpad]
    normer = dists[:, -1]
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 5 — Voting Columns  (K=%d + Kpad=%d)", k, kpad)
    _logger.debug("%s", SEP)
    _logger.debug("  voting cols  %s", _stats(voting))
    _logger.debug("  normer col   %s", _stats(normer))

    _, _, valid_cols = _voting_counts(labels, annot_of_desc, k, kpad, query_idx)
    for j in range(k + kpad):
        _logger.debug(
            "  col[%d]  valid=%d/%d (%s)",
            j,
            valid_cols[j],
            dists.shape[0],
            _pct(valid_cols[j], dists.shape[0]),
        )


def stage_filter_counts(
    dists: np.ndarray,
    labels: np.ndarray,
    annot_of_desc: np.ndarray,
    k: int,
    kpad: int,
    query_idx: int,
    same_name_set: set,
) -> None:
    if not _enabled():
        return
    n_qfxs = dists.shape[0]
    voting_annot_all = np.full((n_qfxs, k + kpad), -1, dtype=np.int32)
    for j in range(k + kpad):
        col = labels[:, j]
        valid = (col >= 0) & (col < annot_of_desc.shape[0])
        voting_annot_all[valid, j] = annot_of_desc[col[valid]]

    invalid = (voting_annot_all == query_idx) | np.isin(
        voting_annot_all, list(same_name_set)
    )
    prefix = "  after filter"
    _logger.debug("")
    _logger.debug("  %s", THIN)
    _logger.debug("  Self/Same-Name Filter")
    _logger.debug("  %s", THIN)
    _logger.debug("  query_idx         %d", query_idx)
    _logger.debug("  same_name_set     %d annotations", len(same_name_set))
    total_entries = n_qfxs * (k + kpad)
    filtered = int(invalid.sum())
    _logger.debug(
        "  filtered entries  %d / %d (%s)",
        filtered,
        total_entries,
        _pct(filtered, total_entries),
    )


def stage_lnbnn_weights(weights: list[float]) -> None:
    if not _enabled():
        return
    w = np.array(weights, dtype=np.float64)
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 6 — LNBNN Weights  (match-level)")
    _logger.debug("%s", SEP)
    _logger.debug("  count        %d", len(w))
    _logger.debug("  weights      %s", _stats(w))
    nonzero = int((w > 0).sum())
    _logger.debug(
        "  nonzero      %d (%s)", nonzero, _pct(nonzero, len(w)) if len(w) > 0 else "—"
    )


def stage_match_to_annot(map_annot_to_matches: dict) -> None:
    if not _enabled():
        return
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 7 — Per-Annotation csum Scores")
    _logger.debug("%s", SEP)
    total_m = sum(v[1] for v in map_annot_to_matches.values())
    _logger.debug("  total matches  %d", total_m)
    _logger.debug("  annotations    %d", len(map_annot_to_matches))
    _logger.debug("  %-8s  %10s  %8s  %6s", "annot", "csum", "matches", "avg_w")
    for aid, (s, cnt) in sorted(
        map_annot_to_matches.items(), key=lambda x: x[1][0], reverse=True
    ):
        avg = s / cnt if cnt > 0 else 0.0
        _logger.debug("  %-8s  %10.4f  %8d  %6.4f", str(aid)[:8], s, cnt, avg)


def stage_final(scored: list) -> None:
    if not _enabled():
        return
    _logger.debug("")
    _logger.debug("%s", SEP)
    _logger.debug("  STEP 8 — Final Ranking")
    _logger.debug("%s", SEP)
    _logger.debug("  %-4s  %-8s  %10s  %8s", "rank", "annot", "score", "matches")
    for rank, sm in enumerate(scored[:10], start=1):
        _logger.debug(
            "  %4d  %-8s  %10.4f  %8d",
            rank,
            str(sm.annot_uuid)[:8],
            sm.score,
            sm.num_matches,
        )


# ── Helpers ───────────────────────────────────────────────────────────


def _voting_counts(labels, annot_of_desc, k, kpad, query_idx):
    n_qfxs = labels.shape[0]
    n_total = annot_of_desc.shape[0]
    valid_cols = []
    annot_cols = []
    for j in range(k + kpad):
        col = labels[:, j]
        valid_mask = (col >= 0) & (col < n_total)
        valid_cols.append(int(valid_mask.sum()))
        annot_cols.append(annot_of_desc[col[valid_mask]])
    return n_qfxs, annot_cols, valid_cols

# Algorithmic Differences: wbia-core vs WBIA HotSpotter Pipeline

Last verified: 2026-06-07. Based on source reading of `wildbook-ia/wbia/algo/hots/`.
Phase 1 (Kpad dynamic, name-level scoring, canonical alignment) implemented 2026-06-07.

## Summary

wbia-core implements a **simplified subset** of WBIA's HotSpotter pipeline. The core LNBNN formula (`ndist - vdist`) is identical, but WBIA layers on additional filters, name-level scoring, a smarter normalizer selection rule, and an optional requery mechanism — all of which contribute to the remaining 1.6× score ratio gap.

---

## 1. Normalizer Selection Rule  [TODO — Phase 2]

| | WBIA | wbia-core |
|---|---|---|
| **Default** | `normalizer_rule='name'` | Always `'last'` |
| **'last' rule** | Uses last column of `K+Kpad+Knorm` | Uses last column (hardcoded `Knorm=1, last`) |
| **'name' rule** | Selects normalizer from a different *name ID* than any voting match | Not implemented |

The `'name'` rule (`nn_weights.py:get_name_normalizers`, line 287):
1. Maps all `K+Kpad` voting neighbors + all `Knorm` normalizer candidates to their name IDs
2. Marks any normalizer candidate invalid if its name ID matches any voting neighbor's name ID
3. Also marks invalid if normalizer name == query name
4. Falls back to `Knorm=-1` if no valid normalizer found → that feature match is dropped

**Impact:** With the `'name'` rule, the normalizer is a feature that is *guaranteed different* from all voting candidates. This makes LNBNN more discriminative — the normalizer is truly an "unrelated" feature, so `ndist - vdist` is larger when the match is correct. wbia-core's `'last'` rule can pick a normalizer from the same name as a voting neighbor, producing weaker weights.

> **This is the single biggest algorithmic difference and the most likely source of the remaining score ratio gap.**

---

## 2. Multi-Filter Multiplication

| Filter | WBIA | wbia-core |
|---|---|---|
| `lnbnn` | `ndist - vdist` | `ndist - vdist` |
| `bar_l2` | `1.0 - vdist` | Not implemented |
| `fg` | `sqrt(q_fgw × d_fgw)` | Optional (`fg_on=True`) |
| `ratio` | `1.0 - (vdist/ndist)` with threshold binary mask | Not implemented |
| `const` | `1.0` (every match weighted equally) | Not implemented |

WBIA computes a **per-feature-match score vector** (one column per filter) and then multiplies all active filter values together:

```python
# chip_match.py:1690 — get_fsv_prod_list
return [fsv.prod(axis=1) for fsv in cm.fsv_list]
```

wbia-core only applies LNBNN (and optionally FG as `w *= sqrt(q_fgw × d_fgw)`). It does not multiply `bar_l2` or any other filters.

**Impact:** Even with `bar_l2_on=False, ratio_thresh=False, const_on=False, fg_on=False, normonly_on=False` (the default WBIA config), WBIA's `fsv.prod()` still multiplies a single-column LNBNN score vector — this is equivalent to wbia-core's approach. But if any additional filters are on, WBIA's weights will differ.

**Action:** Verify the default WBIA config used in the parity benchmark. If `bar_l2_on=True` by default, WBIA is computing `lnbnn × bar_l2` while wbia-core computes just `lnbnn`. This would directly cause the 1.6× ratio.

---

## 3. Name-Level Scoring

wbia-core's `score_matches()` does per-annotation `csum` only.

WBIA adds a name-level aggregation step via `scoring.score_chipmatch_list()`:

| Method | Description | File:Line |
|---|---|---|
| `csum` | per-annot csum → per-name max-csum → canonicalize | `chip_match.py:880` |
| `nsum` | per-annot csum → fmech per-name nsum → canonicalize | `chip_match.py:892` |
| `sumamech` | per-annot csum → per-name sum → canonicalize | `chip_match.py:922` |

**`maxcsum`** (`evaluate_maxcsum_name_score`, line 846):
- Groups per-annot csum values by name ID
- Takes `max()` per name (best annot per name)

**`nsum` / `fmech`** (`name_scoring.py:compute_fmech_score`, line 52):
- Combines feature matches across all annots of the same name
- **Enforces each query feature votes at most once per name** using `combo_ids` (xy-merged feature groups)
- Takes the best score per combo group, sums them

**`canonical name scoring`** (`set_cannonical_name_score`, line 1621):
- Propagates name scores back to annotations — only the best annotation per name gets the name score, others get `-inf`

**Impact:** The final ranking is at the *name level*, not the annotation level. Two annotations of the same name are treated as one result.

---

## 4. ChipMatch State Machine

WBIA builds full `ChipMatch` objects (`chip_match.py`, 3039 lines) with:
- `fm_list` — per-annot feature-match pairs `(qfx, dfx)`
- `fsv_list` — per-annot feature-score vectors `(n_matches × n_filters)`
- `fk_list` — per-annot filter key / rank tensors
- `filtnorm_aids` / `filtnorm_fxs` — per-filter normalizer annotations & features
- `name_groupxs` — annotation-to-name grouping indices
- `algo_annot_scores` / `algo_name_scores` — dicts of evaluated scores

wbia-core uses flat `Match` → `ScoredMatch` lists with no intermediate state.

**Impact:** WBIA's ChipMatch preserves normalizer information (`filtnorm_aids/fxs`) and per-filter scores, enabling richer analysis. It also supports the name-level scoring described above.

---

## 5. Requery Mechanism

WBIA can optionally fetch additional neighbors when all `K+Kpad` initial results are in the impossible set (`requery=True`). The `requery_knn()` function (`neighbor_index.py:795`) iteratively queries FLANN, blocking known-impossible annot indices, until enough valid neighbors are found.

wbia-core implements `Kpad` as a simple column budget, but doesn't requery.

**Impact:** If the parity benchmark data has annotations from the same image/name, WBIA's requery could fetch different neighbors than wbia-core's single query. However, this should only matter when Kpad is too small to absorb all impossible neighbors.

---

## 6. Score Normalizer

WBIA has an optional `vt.ScoreNormalizer` (`pipeline.py:894`) that can be applied to LNBNN weights:
- `fuzzyload(partial_cfgstr=...)` — loads pre-trained normalization parameters
- `normalize_scores()` — applies the normalization
- `lnbnn_norm_thresh` — threshold for binary validity mask

wbia-core has no score normalization.

**Impact:** If the WBIA benchmark config has `lnbnn_normer` configured, weights will differ significantly.

---

## 7. Distance Handling Path

Both use `VEC_PSEUDO_MAX_DISTANCE_SQRD = 2.0 * 512² = 524288`.

| Step | WBIA | wbia-core |
|---|---|---|
| FLANN query | Returns raw int32 SSE | Returns raw int32 SSE |
| Divide by 524288 | In `NeighborIndex.knn()` | In `identify()` |
| clip negative | No explicit clip | `np.maximum(raw_dists, 0.0)` |
| sqrt | In `weight_neighbors()` if `sqrd_dist_on=False` | Always in `identify()` |

**Impact:** If `sqrd_dist_on=True` (distances remain squared), WBIA's LNBNN would be `squared_ndist - squared_vdist`, which differs from wbia-core's `sqrt(sq_ndist) - sqrt(sq_vdist)`. But the default is `sqrd_dist_on=False`, so both apply sqrt. The timing difference (before vs after weighting) is irrelevant since weights use the sqrt'd values in both cases.

However, `bar_l2_fn = 1.0 - vdist` uses the *same vdist* as LNBNN. If sqrd_dist_on=True, bar_l2 = 1.0 - squared_dist instead of 1.0 - sqrt(squared_dist).

---

## 8. Chip Extraction & Feature Extraction

Both systems use:
- `pyhesaff` for feature extraction (same vendored submodule: `wbia-tpl-pyhesaff`)
- `cv2.warpAffine` for chip extraction (same OpenCV version in `wildme/wbia:latest` and `wbia-core:latest`)

**Verified byte-identical** (2026-06-07):
- `libhesaff.so` md5 match
- `libsver.so` md5 match
- JPEG decode pixel md5 match
- warpAffine output pixel md5 match

The entire input pipeline is confirmed identical. The gap is in the scoring pipeline.

---

## Verification Checklist for Parity

To isolate the remaining score gap, compare with WBIA running at the **minimal** config:

```python
QueryParams(
    pipeline_root='vsmany',
    K=4, Kpad=0, Knorm=1,
    normalizer_rule='last',       # ← match wbia-core
    lnbnn_on=True,
    bar_l2_on=False,               # ← disable extra filters
    fg_on=False,
    ratio_thresh=False,
    const_on=False,
    normonly_on=False,
    sv_on=False,                   # ← disable spatial verification
    sqrd_dist_on=False,
    requery=False,
    score_method='csum',
)
```

If this config produces the same results as wbia-core, the gap is in the normalizer rule or extra filters. If not, something else differs.

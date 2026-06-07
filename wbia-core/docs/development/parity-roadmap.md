# Parity Roadmap: wbia-core → WBIA HotSpotter

Last updated: 2026-06-07

## Baseline (run 184326)

15 annots, 2 queries, seed=10, vsmany pipeline, K=4, Knorm=1,
fg_on=False, sv_on=False, norm_rule=last, score_method=nsum (WBIA) / csum (core).

| Metric | wbia-core vs wbia-develop |
|---|---|
| Spearman ρ | 0.987 |
| Top-1 agreement | 100% |
| Top-3 overlap | 100% |
| Score ratio | ~0.8× |

The LNBNN formula, chip extraction (warpAffine), and FLANN query are functionally
correct. Remaining gap is in scoring *aggregation* and config completeness.

## Phase 1 — Scoring depth (highest impact)

### 1a. Kpad dynamic  [IMPLEMENTED]

Currently `Kpad=0` hardcoded. When the query annot is in the database, WBIA pads
K by the count of impossible annotations so self-match/same-name hits don't
consume voting columns.

**Files:** `config.py`, `pipeline.py`

### 1b. Name-level scoring — nsum/fmech  [IMPLEMENTED]

WBIA's default `score_method='nsum'` groups by name, then by query feature
index, takes max per (name, qfx) group, sums survivors. This prevents
double-counting when multiple annots of the same name match the same query
feature.

**Reference:** `wildbook-ia/wbia/algo/hots/name_scoring.py:53` (`compute_fmech_score`)

**Files:** New `name_scoring.py`

### 1c. Canonical name score alignment  [IMPLEMENTED]

Propagates name-level score to the single best annotation per name (highest csum).
Other annots of the same name get `-inf`.

**Reference:** `wildbook-ia/wbia/algo/hots/name_scoring.py:300`
(`align_name_scores_with_annots`)

**Files:** `name_scoring.py`

## Phase 2 — Filter completeness

### 2a. Normalizer rule `'name'`

Documented as the single biggest algorithmic difference. The `'name'` rule
selects a normalizer from a *different name ID* than any of the top-K voting
neighbors, producing more discriminative LNBNN weights.

**Reference:** `wildbook-ia/wbia/algo/hots/nn_weights.py:287`
(`get_name_normalizers`)

**Files:** `scoring.py` or new `nn_weights.py`, `config.py`, `pipeline.py`

### 2b. `bar_l2` filter

Formula: `1.0 - vdist`. Defaults off in WBIA. With both lnbnn and bar_l2
active, combined score = `(ndist - vdist) × (1.0 - vdist)`.

**Reference:** `wildbook-ia/wbia/algo/hots/nn_weights.py:474` (`bar_l2_fn`)

**Files:** `scoring.py`, `pipeline.py`

### 2c. `ratio` filter

Formula: `1.0 - (vdist / ndist)`, thresholded. Config field `ratio_thresh`
already exists in `HotSpotterConfig` but is not wired into the pipeline.

**Reference:** `wildbook-ia/wbia/algo/hots/nn_weights.py:448` (`ratio_fn`)

**Files:** `scoring.py`, `pipeline.py`

## Phase 3 — Config and edge cases

### 3a. Requery mechanism

When all K+Kpad neighbors are in the impossible set, WBIA iteratively queries
FLANN with increasing K until enough valid neighbors are found.

**Reference:** `wildbook-ia/wbia/algo/hots/requery_knn.py`

**Files:** New `requery_knn.py`, `pipeline.py`

### 3b. Score normalizer

Parameterized score rescaling via `ScoreNormalizer` with pre-trained params.
Default is off (no normalizer configured).

**Reference:** `wildbook-ia/wbia/algo/hots/pipeline.py:912-927`

**Files:** New `score_normalizer.py`

### 3c. `const` filter

Uniform weight of 1.0 for every match. Trivial to implement.

**Reference:** `wildbook-ia/wbia/algo/hots/nn_weights.py:68` (`const_match_weighter`)

## Verification checklist (WBIA minimal config match)

The benchmark `DEFAULT_CONFIG` in `run_benchmark.py` already matches WBIA's
default vsmany settings:

```python
DEFAULT_CONFIG = {
    "pipeline_root": "vsmany",
    "K": 4,
    "Knorm": 1,
    "Kpad": 0,
    "kpad_policy": "fixed",
    "score_method": "nsum",        # WBIA default → fmech path
    "normalizer_rule": "last",
    "fg_on": False,
    "bar_l2_on": False,
    "sv_on": False,
}
```

To test with `normalizer_rule='name'` (Phase 2), override at runtime:

```bash
# Not yet exposed as CLI flag — edit DEFAULT_CONFIG or add --score-method flag
python3 tests/benchmark/run_benchmark.py \
  --targets wbia-core wbia-develop \
  --n-annots 15 --n-queries 2 --seed 10
```

## Effort summary

| Step | Effort | Impact | Status |
|---|---|---|---|
| 1a. Kpad dynamic | Small | Medium | DONE |
| 1b. nsum/fmech name scoring | Medium | High | DONE |
| 1c. Canonical name alignment | Small | High | DONE |
| 2a. Normalizer rule 'name' | Medium | High | TODO |
| 2b. bar_l2 filter | Small | Low | TODO |
| 2c. ratio filter | Small | Low | TODO |
| 3a. Requery | Medium | Low | TODO |
| 3b. Score normalizer | Small | Low | TODO |
| 3c. const filter | Tiny | Low | TODO |

## Benchmark configuration

The benchmark runner now:
- Sets `score_method: "nsum"` (WBIA fmech path) in `DEFAULT_CONFIG`
- Creates deterministic `name_uuid` from COCO `individual_ids` so annotations
  of the same individual share a name — enables meaningful name-level scoring
- Passes `kpad_policy`, `normalizer_rule`, `bar_l2_on`, `const_on` through
  the sidecar to `HotSpotterConfig`

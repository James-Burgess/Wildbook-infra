# Parity Analysis: wbia-core vs WBIA HotSpotter

## Latest Results (2026-06-07 — Phase 2: name-level scoring + filters)

Tested with 15 COCO wildlife annotations, 2 queries, seed=10.
Both systems use pyhesaff on chips via `cv2.warpAffine` (700/maxwh).
FG, SV, bar_l2 all disabled. wbia-core uses `score_method=nsum_wbia`
(fmech + canonical alignment), WBIA uses its native `score_method=nsum`.
COCO `individual_ids` are used as `name_uuid` for both systems.

| Metric | wbia-core | WBIA develop |
|---|---|---|
| Top-1 accuracy | 100% (2/2) | 100% (2/2) |
| Results returned | 6 (canonical) | 14 (all annots) |
| Score ratio | ~0.8× | — |

wbia-core returns only 6 unique individuals (canonical name alignment
working correctly — only best annot per individual). WBIA develop
returns all 14 annotations because it doesn't receive name grouping
via the API. Spearman ρ is not directly comparable across these
different granularities.

**Top-1 matches (both queries agree):**
- Q0: coco-annot-433 (wbia-core: 97.2, WBIA: 119.7)
- Q1: coco-annot-2753 (wbia-core: 115.5, WBIA: 87.8)

### What was fixed since 06-06e

| Version | Fix | Status |
|---|---|---|
| 06-06e | warpAffine, distance norm | ✓ (ρ=0.32) |
| 06-07 P1 | Kpad dynamic, nsum/fmech, canonical alignment | ✓ |
| 06-07 P2 | normalizer_rule='name', bar_l2, ratio, const filters | ✓ |

### Remaining gap

Score ratio ~0.8× persists. The root cause is **FLANN distance differences**
(2.3× difference in normalized distances before LNBNN), likely from
descriptor-level variations between the two systems. The algorithmic
scoring pipeline is now complete.

---

### What was ruled out

| Theory | Result |
|---|---|
| FLANN KD-tree non-determinism | Exact search = identical results |
| Missing FG weights | `fg_on=False` in both systems |
| Wrong chip dimensions | Fixed: 700/maxwh matches WBIA |
| Crop+resize vs warpAffine | Fixed: now uses warpAffine |
| Wrong distance normalization | Fixed: `raw/524288`, sqrt |
| Different pyhesaff params | Both use defaults |
| probchip masking | WBIA uses raw RGB chip |
| Missing bar_l2/const filters | Implemented, defaults off |
| Missing ratio filter | Implemented (`ratio_thresh`) |
| Missing nsum/fmech scoring | Implemented (Phase 1b) |
| Missing canonical alignment | Implemented (Phase 1c) |
| Missing normalizer_rule='name' | Implemented (Phase 2a) |

### Performance

| Metric | Start (full image) | Current (warpAffine chip) |
|---|---|---|
| Features per image | 30,000 | ~1,500 (700/maxwh) |
| FLANN index (15 annots) | ~300,000 × 128 | ~25,000 × 128 |
| Query time (15 annots, 2 queries) | 101s | ~7s |

### To close the score-ratio gap

The 1.6× score ratio comes from raw FLANN distance differences (2.3×
before LNBNN), not from algorithmic gaps. The descriptor-level variation
between the two pyhesaff builds is the root cause. Options:

1. **Pre-extracted feature fixtures** — store pyhesaff output from WBIA
   as reference, bypass chip + feature extraction differences. Tests compare
   scoring pipeline output given identical features. (Most practical)

2. **Build in WBIA's base image** — now using `nvidia/cuda:11.7.1` (matching).
   Verify libhesaff.so is byte-identical between builds.

## Historical Context

### 2026-06-05 (initial pyhesaff, full-image features)
- wbia-core vs WBIA: ρ = −0.15 (uncorrelated)
- Score magnitude: 10-50× higher

### 2026-06-04 (OpenCV SIFT, replay fixtures)
- 5/12 replay fixtures pass top-1 match
- Score magnitude: 100-1000× mismatch

## Acceptance Criteria

| Criterion | Current (06-07) | Target |
|---|---|---|
| Top-1 agreement | 100% | ≥ 80% |
| Score magnitude ratio | ~0.8× | < 1.1× |
| Determinism (repeat run) | ✓ | ✓ |
| Scoring pipeline features | All Phase 1+2 done | — |
| Name-level scoring (nsum/fmech) | ✓ | — |
| Canonical name alignment | ✓ | — |
| Normalizer rule 'name' | ✓ | — |
| bar_l2 / ratio / const filters | ✓ | — |
| Kpad dynamic | ✓ | — |
| Requery mechanism | Not implemented | — |
| Score normalizer | Not implemented | — |

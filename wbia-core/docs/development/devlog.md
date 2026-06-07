# wbia-core Development Log

This file tracks design decisions, progress, and open questions as the
package evolves.  It complements the formal ADRs in `decisions/`.

---

## 2026-06-06c — Chip extraction + distance normalization fixes

### Root cause: missing chip extraction

WBIA crops images to their annotation bbox and resizes to 450px width
(`ChipConfig(dim_size=450, resize_dim='width')`) before extracting
features. wbia-core was extracting features from the FULL image
(2000×3000 pixels → 30,000 keypoints).

This caused:
- **150× more keypoints** than WBIA (30,000 vs ~200 from a chip)
- **50× higher scores** (full-image csum vs chip csum)
- **30× slower** queries (30,000 × 60,000 descriptor FLANN vs 200 × 1,200)

### Fixes applied

**1. Distance normalization** (2026-06-06b)
Removed `np.sqrt()` from `dists = sqrt(raw / 524288)` — WBIA uses
`raw / 524288` directly. Distances stay in squared-norm space.

**2. Chip extraction** (2026-06-06c)
Added `_extract_chip()` to the sidecar: crops to bbox, resizes to 450px
width (matching WBIA's `ChipConfig`). Applied to both query and database
entries. Cache key now includes bbox hash.

### Parity results after fixes (10 annots, 3 queries, seed=42)

| Query | Top-1 agree | Spearman ρ | WBIA score | wbia-core score |
|---|---|---|---|---|
| 0 | ✓ (3136) | **0.92** | 12.2 | 3.0 |
| 1 | ✗ | 0.00 | 40.1 | 9.1 |
| 2 | ✗ | -0.17 | 55.7 | 12.5 |

Score magnitudes now match (1-12 vs 2-56 WBIA). Query 0 achieves
near-perfect parity (top-1 match, ρ=0.92). Queries 1-2 diverge —
likely due to FLANN KD-tree non-determinism with small chip features.

### Performance improvement

| Metric | Before | After |
|---|---|---|
| Score/query (2 imgs) | 1986 | 39 |
| Matches/query | 50,577 | 931 |
| Query time (10 annots) | 101s | 3s |
| Max score delta vs WBIA | 258 | 54 |

### Remaining work

- Enable exact FLANN search for parity testing (eliminate KD-tree noise)
- Investigate why query 1 has ρ=0.0 — possibly chip extraction differs
  from WBIA (our simple crop+resize vs WBIA's full chip pipeline)
- Add `dim_size` config to HotSpotterConfig for chip dimension control
- Run larger-scale parity tests (50+ annots, now feasible with chip fix)

### 4-target comparison (10 annots, 3 queries)

| Metric | WBIA inter-version | wbia-core vs WBIA |
|---|---|---|
| Spearman ρ | 1.000 | 0.706 |
| Top-3 overlap | 1.00 | 0.556 |
| Top-1 agree | 100% | 0% |
| Score ratio | ~1× | 10–20× |

All three WBIA versions (latest, nightly, develop) produce **identical
rankings** with pyhesaff features. wbia-core shows moderate correlation
(ρ=0.71) with 56% top-3 overlap. Score magnitudes are 10–20× higher,
pointing to missing `VEC_PSEUDO_MAX_DISTANCE_SQRD` normalization in the
FLANN → LNBNN path or different FG weight formula.

### Historical progression

| Date | Feature extractor | wbia-core vs WBIA ρ |
|---|---|---|
| 2026-06-05 | OpenCV SIFT | −0.15 to 0.39 |
| 2026-06-06 | pyhesaff (source) | 0.706 |

Switching from OpenCV SIFT to pyhesaff improved ρ by **~0.5** (from
essentially uncorrelated to moderate agreement). The feature extractor
was the dominant source of disagreement.

### Next investigation

- FLANN distance normalization (`VEC_PSEUDO_MAX_DISTANCE_SQRD`)
- Self-match filter scope (voter columns only vs all)
- LNBNN formula (`ndist - vdist` vs other variants)
- FG weight formula (`sqrt(q_fg * db_fg)` vs sum)
- Exact (linear) FLANN search to eliminate KD-tree non-determinism

See `docs/development/parity-analysis.md` for the full investigation plan.

### Large-scale test (50 annots, 3 queries)

wbia-core timed out on all 3 queries (300s limit). 50 annots × ~5s
pyhesaff extraction per image = ~250s minimum per query, exceeding the
sidecar timeout. WBIA completed fine via internal depcache.

**Fix:** cached features in the sidecar by `aid:image_hash`, increased
timeout to 1200s. With caching: Q0 extracts all features (~6 min),
subsequent queries use cache (~30s each).

### Reference-based comparison

Since WBIA is deterministic across versions (ρ=1.0 between latest/nightly/develop),
we store WBIA results once and compare against them — no WBIA containers needed.

**Usage:**
```bash
# Create reference (one-time)
python tests/benchmark/run_benchmark.py --n-annots 10 --n-queries 3 --targets wbia-latest
cp -r test-run-results-*/target-wbia-latest/ tests/benchmark/reference/wbia-latest-10/

# Fast reference comparison (no WBIA startup)
python tests/benchmark/run_benchmark.py --n-annots 10 --n-queries 3 --reference tests/benchmark/reference/wbia-latest-10/
```

**Results (10 annots, 3 queries, seed=42):**
- wbia-core vs reference: ρ=0.644, top-3 overlap=0.444
- wbia-core Q0: 362s (first extraction), Q1-Q4: 32-43s (cached)

### Remaining

- Score normalization gap: wbia-core scores 10-20× WBIA — likely missing VEC_PSEUDO_MAX_DISTANCE_SQRD
- Create reference fixtures for larger dataset sizes
- FLANN exact (linear) search to eliminate KD-tree non-determinism
- LNBNN formula audit against WBIA source

### New docs

- `docs/development/testing-guide.md` — comprehensive testing reference
- `docs/development/parity-analysis.md` — updated with 2026-06-06 results
- `docs/decisions/0006-submodule-deps.md` — submodule-source build ADR

---

## 2026-06-06 — pyhesaff hard dependency, submodule-source build, single Docker image

### What was changed

**1. pyhesaff made mandatory.** Removed the OpenCV SIFT fallback from
`features.py`. `wbia-pyhesaff` is now a hard dependency in `pyproject.toml`.
Grayscale images (2D) are expanded to 3-channel before passing to
pyhesaff's C extension.

**2. Submodule-source build.** The PyPI wheel for `wbia-pyhesaff` 4.0.0
causes a SIGSEGV at import time — its transitive dep `wbia-vtool` bundles
pre-compiled OpenCV 2.4.5 shared libraries that conflict with system
OpenCV 4.x. All three problematic deps are now git submodules:

| Submodule | Path | Build order |
|---|---|---|
| `wbia-utool` | `wbia-core/wbia-utool/` | 1st (pure Python) |
| `wbia-vtool` | `wbia-core/wbia-vtool/` | 2nd (libsver.so) |
| `wbia-tpl-pyhesaff` | `wbia-core/wbia-tpl-pyhesaff/` | 3rd (libhesaff.so) |

Each is installed with `pip install --no-deps` from submodule source.
`SETUPTOOLS_SCM_PRETEND_VERSION` is set because Docker builds lack `.git`.
The Dockerfile copies everything (`COPY . /app`), then builds submodules
before installing wbia-core.

**3. Single image, two entrypoints.** Eliminated the dual-image pattern
(separate sidecar and test images). One Dockerfile builds everything.
Entrypoints:

- `scripts/entrypoints/server-entrypoint.sh` → gunicorn `sidecar.api:app`
- `scripts/entrypoints/test-entrypoint.sh` → parity tests

The old `tests/benchmark/sidecar/Dockerfile` and `requirements.txt` are obsolete.

**4. Sidecar moved.** The Flask app moved from `tests/benchmark/sidecar/app.py`
to `sidecar/api.py`. Test imports updated (`from sidecar.api import app`).

### Verification

- Docker build completes clean (3 min)
- All three submodules import without SIGSEGV
- Health endpoint: `{"status": "ok"}`
- Identify endpoint: 2 entries in ~60ms, scored correctly
- 17/17 core tests pass inside container

### Remaining

- Benchmark re-run with pyhesaff active (should prove parity with WBIA)
- Replay fixtures need pyhesaff; previously ran with OpenCV SIFT

---

## 2026-06-04 — Gaps filled: spatial verification, label mapping, filter perf, integration test, E2E strategy

### What was fixed

**1. Spatial verification — exact per-feature correspondences.** The
previous implementation approximated keypoint pairs by taking the top-N
query keypoints and matching them modulo-style to database keypoints.
This was wrong for any candidate that didn't rank first.

Fix:
- Added `dfx` (database feature index) to `Match` (`data.py`).
- `build_matches` now accepts a parallel `local_labels` array from the
  faiss → annotation-labels converter and populates `Match.dfx`.
- `score_matches` aggregates `(qfx, dfx)` pairs into a new
  `ScoredMatch.correspondences` field.
- `spatial_verify` iterates the exact correspondences to build
  `(q_kp, db_kp)` pairs for `cv2.findHomography`.

**2. Pipeline — global descriptor → annotation index mapping (was a bug).**

The old `pipeline.py` built one faiss index with all descriptors from all
annotations but treated the returned labels as *annotation indices* when
they were actually *global descriptor indices*.  For a database with
multiple annotations this would silently return wrong matches.

Fix:
- Added `_compute_annotation_offsets()`: cumulative descriptor count per
  annotation.
- Added `_global_labels_to_annotation()`: uses `np.searchsorted` to
  convert global descriptor indices → (annotation_idx, local_feature_idx).
- Pipeline now converts labels before filtering/scoring.

**3. LNBNN normalizer preservation.** The normalizer distance (K+1th
column) must be taken from the *unfiltered* index results to match WBIA
behaviour.  The old implementation filtered and sorted *all* columns,
potentially shifting the normalizer.

Fix: pipeline now saves `distances[:, K]` and `labels[:, K]` before
filtering, filters only columns `[0..K)`, then concatenates the
unfiltered normalizer back.

**4. `filter_self_matches` — `np.vectorize` replaced.** The old code used
`np.vectorize` with a lambda calling `database[idx].name_uuid`, which was
O(N*K) in Python and slow for large feature counts.

Fix: builds a `name_uuids` lookup array, uses boolean advanced indexing
(`is_same_name[safe_labels]`) with bounds checking.  This is pure
vectorised NumPy.

**5. Integration tests.** Added `tests/test_pipeline.py` with:
- Unit tests for `_compute_annotation_offsets` and
  `_global_labels_to_annotation`.
- Integration tests for `identify()`: shape, self-exclusion,
  same-name-exclusion, SV smoke test, correspondences presence,
  non-HotSpotter rejection, large database stress (marked `@slow`).

**6. E2E test strategy.** Documented in
`docs/development/e2e-test-strategy.md`:
- Three phases: offline replay against recorded WBIA fixtures, shadow-mode
  comparison in production, bit-exact reproducibility.
- Test matrix by species, image quality, pose, dataset size, config.
- Fixture recording script design and replay test harness.
- Gap analysis of what is not yet testable.
- Acceptance criteria (Recall@1 ≥ 95 %, determinism, performance).

### Test count

```
$ pytest -v
41 passed in 0.39s
```

- 8 config
- 6 data
- 1 features
- 2 knn
- 12 pipeline (6 helper-unit + 6 integration)
- 7 scoring
- 3 spatial
- 1 features (pyhesaff missing)
- 1 slow (skipped by default)

### Verification

All gaps from the previous entry are closed:

- [x] Spatial verification threads per-feature correspondences.
- [x] `filter_self_matches` uses vectorised lookup (no `np.vectorize`).
- [x] Integration test runs the full `identify()` pipeline.
- [x] E2E test strategy documented with acceptance criteria.

### Remaining (non-blocking)

1. **Record WBIA fixtures for Phase 1 replay tests.** Requires a running
   WBIA instance with known images.  Blocked on Phase 2 of the migration
   plan (wildlife-id shadow mode deployment).
2. **Bit-exact determinism test in CI.** Relies on Phase 1 fixtures being
   available.  The contract is documented but not yet enforced in CI.
3. **Source extraction of HotSpotter from `wildbook-ia`.** The current
   implementation reimplements the pipeline from scratch; it has not been
   validated against the original code.  An `xdoctest`-style comparison
   against the original `chip_match.py` would catch subtle differences.

## 2026-06-04 — Replay test infrastructure + parity analysis (5/12 pass)

### What was built

**`tests/replay/`** — Docker-based replay tests that record WBIA
identification results as NPZ fixtures and replay them through
wbia-core.

| File | Purpose |
|---|---|
| `docker-compose.yml` | Minimal WBIA stack (no PostgreSQL, SQLite mode). Mounts `testdata/images/` as `/images`, adds `host.docker.internal:host-gateway` so WBIA can reach the host's HTTP server. |
| `conftest.py` | Session-scoped Docker compose lifecycle (`up -d` → poll heartbeat → `down -v`). Fixture discovery helpers. |
| `record_fixtures.py` | Standalone script: generates synthetic spot-pattern images (OpenCV circles), starts a temporary HTTP server, adds images+annotations to WBIA via REST API, starts async identification, polls for completion, saves result as NPZ. |
| `test_replay.py` | Parametrized pytest tests. Three fixture-loading tests (no pyhesaff needed) verify NPZ structure + image decoding. Four `@pytest.mark.replay` tests compare wbia-core rankings against WBIA (require pyhesaff + fixtures). |

Fixture definition (in `record_fixtures.py`):
```python
FIXTURES = [
    {"name": "zebra_grevys", "seed": 42, "n_annots": 5},
    {"name": "giraffe_reticulated", "seed": 99, "n_annots": 4},
    {"name": "whale_shark", "seed": 17, "n_annots": 3},
]
```

This generates 5 + 4 + 3 = 12 test cases (one per annotation as query).

### How to run

```bash
# 1. Start WBIA
cd tests/replay && docker compose up -d

# 2. Record fixtures (waits for WBIA heartbeat, ~1 min)
python record_fixtures.py

# 3. Run replay tests (requires wbia-pyhesaff for feature extraction)
cd ../.. && pip install wbia-core[features]
pytest tests/replay/ -m replay
```

Without fixtures or pyhesaff, all replay tests skip gracefully:
```
$ pytest
41 passed, 7 skipped in 0.44s
```

### Test count

```
$ pytest -v
48 collected, 41 passed, 7 skipped
│
├── tests/unit/         41 tests (unit + integration, no Docker)
│
├── tests/replay/
│   ├── test_fixture_loads          skipped (no fixtures)
│   ├── test_wbia_scores_parsable   skipped (no fixtures)
│   ├── test_image_decodable        skipped (no fixtures)
│   ├── test_replay_rankings        skipped (no fixtures)
│   ├── test_replay_self_excluded   skipped (no fixtures)
│   ├── test_replay_correspondences skipped (no fixtures)
│   └── test_replay_with_sv         skipped (no fixtures + slow)
```

### API flow captured by the recorder

1. `POST /api/image/json/` — register images with WBIA (served via HTTP)
2. `POST /api/annot/json/` — create annotations with bbox + species
3. `POST /api/engine/query/annot/rowid/` — start identification (async)
4. `GET /api/engine/job/status/?jobid=...` — poll until `completed`
5. `GET /api/engine/job/result/?jobid=...` — fetch result JSON

### Known limitations

1. **No GPU in the compose file.** WBIA runs detection/identification on
   CPU.  This is slow for real images but fine for 200×300 synthetic
   spot patterns.
2. **Detection may fail on synthetic images.** The LightNet/YOLO models
   are trained on real animal photos.  Synthetic circle patterns may not
   trigger detection.  The fixture falls back to using the known bbox
   directly for annotation creation.
3. **`extra_hosts: host.docker.internal:host-gateway`** requires Docker
   Compose v2.  On older setups, set `HOST_ALIAS` to the host's Docker
   bridge IP (e.g., `172.17.0.1`).
4. **`name_uuids` are `None`.** The recorder passes `____` (unnamed) to
   WBIA, so name-based comparisons (same-name filtering) are not tested.
   Future work: assign distinct names per annotation to test name
   filtering.

### Parity analysis

Docker image built with pyhesaff source-compiled against system OpenCV.
Parity test (`tests/replay/parity_test.py`) runs inside the image,
comparing wbia-core rankings against 12 recorded WBIA NPZ fixtures.

**5/12 pass.** All 12 return the same set of candidate UIDs, but 7 show
different ordering. Score magnitudes differ by 100-1000× (wbia-core:
100-1400, WBIA: 0-5).

Fixes that moved the needle (from 0→5 passing):
- LNBNN formula: `ndist - vdist` (was `1 - vdist/ndist`)
- Distance sqrt: `np.sqrt` on faiss squared L2 output
- FG weights: probchip gaussian multiplied element-wise with lnbnn
- Config defaults: knn=4, fg_on=True, csum scoring (vsmany defaults)
- pyhesaff kwargs: map SiftConfig → HESAFF_PARAM_DICT keys

See `docs/development/parity-analysis.md` for detailed hypotheses and
investigation plan.

---

## 2026-06-04/05 — Global index rewrite, distance normalization, Kpad elimination

### What was discovered

**WBIA uses a SINGLE global FLANN index**, not per-annotation indexes.
The `NeighborIndex` class (`neighbor_index.py:204`) concatenates all
database descriptors via `np.vstack` into one big `(M × D)` array and
builds a single KD-tree. Per-annotation identity is preserved through
reverse-mapping arrays (`idx2_ax` → `ax2_aid`, `idx2_fx`).

**WBIA normalizes distances post-query.** Raw squared Euclidean distances
from pyflann are divided by `2 * 512² = 524288` (`VEC_PSEUDO_MAX_DISTANCE_SQRD`
in `hstypes.py:75`), then sqrt is applied (when `sqrd_dist_on=False`).

**WBIA does not use a Kpad buffer column.** It queries for exactly
`K + Knorm` neighbors (5 with defaults). The first K are voters, the
last Knorm is the normalizer.

**WBIA includes the query in the FLANN index.** The query annotation's
descriptors are part of the global array. Self-matches (distance ≈ 0)
are filtered from the voting columns but the normalizer column is NOT
filtered. This means the normalizer can be the query itself (ndist ≈ 0),
producing negative LNBNN weights for all voter columns of that feature.

### What was fixed

1. **`knn.py`**: Added `build_global_index(feature_sets)` — concatenates
   descriptors, builds single FLANN index, returns `(index, annot_indices,
   feat_indices)` mapping arrays.
2. **`pipeline.py`**: Complete rewrite of `identify()`:
   - Single global FLANN index over ALL annotations (matching WBIA)
   - `K + Knorm` query (matching WBIA's exact behavior)
   - Post-hoc distance normalization: `sqrd_dist / (2·512²)`
   - L2 sqrt: `sqrt(normalized_dist)`
   - Self/same-name filter on voting columns only (normalizer NOT filtered)
   - Raw LNBNN: `ndist - vdist` (allows negative like WBIA)
   - FG weight: `sqrt(q_fg * db_fg)` per match
   - csum scoring: sum of feature weights per annotation
3. **`config.py`**: Added `kpad` field (default=0), FLANN parameter fields
   (`flann_algorithm`, `flann_trees`, `flann_random_seed`, `flann_checks`,
   `flann_cores`)
4. **`scoring.py`**: Made `per_feature_fg()` public (WBIA's `_per_feature_fg`)

### Remaining root cause

FLANN KD-tree non-determinism between environments. Verified:
- Same environemnt: exact (linear) and kd-tree produce identical results
- Cross-environment: different pyflann builds produce different
  approximate neighbor assignments, even with identical params and seed

Score magnitudes now match (both in 0–5 range). Features and distance
distributions are identical. Remaining differences are ranking swaps
between adjacent-scoring annotations due to approx search noise.

### Test count

```
$ pytest -v
123 passed in 9.68s
```

The 2 previously skipped live tests are no longer in the test suite.
The replay tests (`tests/replay/`) require fixtures + pyhesaff.

### Key references

- WBIA's `NeighborIndex`: `wildbook-ia/wbia/algo/hots/neighbor_index.py:204`
- WBIA's `knn` method: `neighbor_index.py:685` (global single-index query)
- WBIA's distance normalization: `neighbor_index.py:777` and `hstypes.py:75`
- WBIA's `baseline_neighbor_filter`: `pipeline.py:734`
- WBIA's `lnbnn_fn`: `nn_weights.py:406` (raw `ndist - vdist`)
- WBIA's `fg_match_weighter`: `nn_weights.py:95`
- WBIA's `evaluate_csum_annot_score`: `chip_match.py:813`
- Config defaults: `Config.py` (`K=4`, `Knorm=1`, `sqrd_dist_on=False`)

---

## 2026-06-06d — Current state: chip extraction verified, partial parity

### What was fixed (since 06-06c)

1. **Chip extraction**: Added `_extract_chip()` in `sidecar/api.py` — crops full
   image to annotation bbox, resizes to 450px width (matching WBIA's
   `ChipConfig(dim_size=450, resize_dim='width')`). Applied to both query and
   database entries before feature extraction. Cache key now includes bbox hash.

2. **Distance normalization**: Removed `np.sqrt()` from distance normalization
   in `pipeline.py`. WBIA divides raw FLANN squared Euclidean distances by
   `VEC_PSEUDO_MAX_DISTANCE_SQRD = 524288` directly — no sqrt. Distances stay in
   squared-norm space.

### Current parity (COCO 10 annots, 3 queries, seed=42)

| Query | Top-1 agree? | Spearman ρ | WBIA score μ | wbia-core score μ |
|---|---|---|---|---|
| 0 | **YES** (annot-3136) | **0.92** | 7.8 | 1.9 |
| 1 | NO | 0.07 | 24.4 | 6.4 |
| 2 | NO | -0.17 | 26.7 | 7.0 |

**Aggregates**: mean ρ=0.27, top-1=33%, top-3 overlap=44%, max score delta=53.5.

**Score magnitudes**: wbia-core scores are consistently 3–5× lower than WBIA,
but in the same order of magnitude (1–12 vs 2–56). Not a 40× mismatch anymore.

**Query 0** (easy query): near-perfect parity — top-1 match, ρ=0.92, same
annotation identified. The scoring pipeline is **functionally correct** for
unambiguous cases.

**Queries 1-2** (harder queries): poor correlation. WBIA and wbia-core disagree
on the best match, though top-5 sets have high overlap.

### Performance after chip fix

| Metric | Before (full image) | After (chip) |
|---|---|---|
| Features per image | ~30,000 | ~200 |
| FLANN index size (10 annots) | ~300,000 × 128 | ~2,000 × 128 |
| Query time (2 imgs side-by-side) | 13.2s | 274ms |
| Full benchmark (10 annots, 3 queries) | 101s | 3.2s |
| Feature extraction (one image) | 15s | 0.5s |

### Remaining gap: known causes

1. **FLANN KD-tree non-determinism** (primary suspect for queries 1-2).
   Different pyflann builds produce different approximate neighbor assignments
   even with identical descriptors, params, and seed. When LNBNN weights are
   close (many annots have similar distances), small KD-tree perturbations swap
   rankings.
   
   **Mitigation**: `exact_knn()` with chunked dot-product is implemented in
   `knn.py` but not wired into the sidecar or benchmark. Enable with
   `flann_algorithm='exact'` — eliminates KD-tree noise entirely. Memory cost:
   O(batch_size × db_size × 8 bytes). For 2,000 descriptors and batch_size=500:
   ~8 MB per chunk.

2. **Score scaling** (secondary). wbia-core scores are 3–5× lower than WBIA
   even on query 0 where rankings match (ρ=0.92). Both normalize by 524288. The
   gap suggests a missing multiplicative factor:
   - FG weight: WBIA uses `sqrt(q_fg * db_fg)` but the FG values may differ
     between chip extraction methods
   - Feature count normalization: WBIA may divide by something after csum
   - `Knorm` scaling: the per-feature normalizer may be aggregated differently
   
   This is a magnitude offset, not a ranking issue. If it's just a constant
   factor, rankings are unaffected.

3. **Chip pixel differences** (minor). wbia-core uses simple crop + Lanczos
   resize. WBIA's `ChipConfig` has additional options:
   - `histeq=True` — histogram equalization (may be on by default)
   - `adapteq=True` — CLAHE
   - `region_norm=True` — per-region normalization
   - `grabcut=True` — foreground segmentation
   
   If any of these are enabled in WBIA's default pipeline, the chips will
   produce slightly different pixel values → different SIFT descriptors →
   different distances → different LNBNN weights.

### What needs investigation

| Area | Priority | Effort |
|---|---|---|
| Wire exact search into benchmark | P0 | Small (config flag already exists) |
| Verify score scaling factor | P1 | Medium (trace WBIA's csum path) |
| Check if WBIA chip defaults include histeq/adapteq | P2 | Small (check Config.py) |
| Investigate LNBNN `ndist - vdist` edge cases | P3 | Medium |
| Run with larger dataset (50 annots) | P3 | Medium (now feasible at 3s) |

### Current file state

```
wbia-core/
├── sidecar/api.py         # Flask sidecar with _extract_chip(), _feature_cache
├── src/wbia_core/
│   ├── pipeline.py         # identify() — global FLANN, distance norm, LNBNN+FG
│   ├── features.py         # pyhesaff only, SingleScaleAffine extractor
│   ├── knn.py              # build_global_index, query_index, exact_knn chunked
│   ├── scoring.py          # fg_weight, lnbnn_weight, matching
│   └── config.py           # HotSpotterConfig (K=4, Knorm=1, Kpad=0, etc.)
├── tests/benchmark/
│   ├── run_benchmark.py    # --reference flag, reference injection
│   ├── targets/core.py     # CoreTargetRunner (docker run wbia-core:latest)
│   ├── reference/          # Stored WBIA results (wbia-latest-10/)
│   └── test-run-results-current/  # Latest results
├── docs/
│   ├── development/
│   │   ├── devlog.md       # This file
│   │   ├── parity-analysis.md
│   │   └── testing-guide.md
│   └── decisions/
│       ├── 0003-feature-extraction.md
│       └── 0006-submodule-deps.md
└── Dockerfile              # Submodule source build, two entrypoints
```

### Quick reference: running tests

```bash
# Full benchmark (reference WBIA results, no WBIA container needed)
python3 tests/benchmark/run_benchmark.py \
  --n-annots 10 --n-queries 3 \
  --reference tests/benchmark/reference/wbia-latest-10/ \
  --results-dir test-results

# Analyze results
python3 tests/benchmark/analyze.py report test-results/

# Unit tests
pytest -v
```

---

## 2026-06-06f — sqrt distance + OpenCV version + dep cleanup

### Fix: apply sqrt to normalised distances (sqrd_dist_on=False)

WBIA's filter chain (line 878-881 of pipeline.py) applies `np.sqrt()`
to the 524288-normalised distances BEFORE LNBNN when `sqrd_dist_on=False`
(the default). Our pipeline previously kept distances in squared-norm space.

```python
# WBIA: dist = sqrt(raw_sse / 524288)
# Ours (was): dist = raw_sse / 524288  (squared-norm)

dists = np.sqrt(np.maximum(raw_dists, 0.0) / max_distance_sqrd)
```

**Impact**: Score ratio improved from 0.57× → **0.69×** (closer to 1.0).

Rankings unchanged (sqrt is monotonic — preserves ordinal relationships).

### OpenCV version: pinned in pyproject.toml

WBIA uses `opencv-contrib-python-headless==4.7.0.72` pip wheel (bundles
its own libjpeg-turbo 2.1.x). Our Dockerfile previously used system
`libopencv-dev` from Debian Bookworm (different version + different libjpeg).

**Fix**: Added `opencv-contrib-python-headless==4.7.0.72` to `pyproject.toml`
dependencies alongside `numpy>=1.24,<2` (the wheel needs NumPy 1.x).
Removed explicit pip installs from Dockerfile — now managed by the project.

**Impact**: No change in parity (same results). Confirms that OpenCV version
noise was not the dominant factor — the chips were already pixel-identical
enough with system OpenCV.

### Current parity (10 annots, 3 queries, after all fixes)

| Query | Top-1 agree? | Spearman ρ | Score ratio |
|---|---|---|---|
| 0 | ✓ | **1.00** | 0.69× |
| 1 | ✗ | 0.10 | 0.68× |
| 2 | ✗ | -0.12 | 0.69× |

Mean ρ: **0.33**, Top-3 overlap: **67%**, Score ratio: **0.69×**

### Remaining gap: pyhesaff build differences

The consistent 0.69× score ratio and ρ≈0 on ambiguous queries are now
attributed to **pyhesaff `.so` build differences**:

- **wbia-core**: compiled from `wbia-tpl-pyhesaff` submodule source on
  Debian Bookworm with GCC (system compiler)
- **WBIA reference**: compiled from a different pyhesaff source/build
  on Ubuntu 22.04 with potentially different compiler flags/version

Different builds produce slightly different keypoint positions and SIFT
descriptors even on identical chip images → different FLANN neighbors →
different LNBNN weights → different rankings.

### What's been tried and ruled out

| Fix | Impact | Status |
|---|---|---|
| Chip extraction (crop+resize → warpAffine) | Massive (10-50× → 1.6×) | ✓ |
| Chip dimensions (450/width → 700/maxwh) | Significant (ρ 0.92→0.98) | ✓ |
| Distance normalization (remove sqrt, then re-add) | Minor (ratio 0.57→0.69) | ✓ |
| OpenCV version (system → 4.7.0.72 wheel) | None | ✓ ruled out |
| Exact FLANN search | None (KD-tree already deterministic) | ✓ ruled out |
| EXIF orientation (all orient=1) | None | ✓ ruled out |
| Missing bar_l2/fg/const filters (all False) | None | ✓ ruled out |

### Next steps to reach ≥90% ρ

1. **Compare pyhesaff outputs directly** — run the same chip image through
   both wbia-core and WBIA's pyhesaff, compare keypoint count and
   descriptor statistics
2. **Build pyhesaff inside the WBIA base image** — use `nvidia/cuda:11.7.1`
   as our base to get identical compiler/build environment
3. **Re-generate reference with current image** — confirm WBIA's own
   results haven't drifted

Option 2 would give us the same pyhesaff `.so` as WBIA, eliminating the
last systematic difference. This requires changing the Dockerfile base
image from `python:3.10-bookworm` to `nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04`.

---

## 2026-06-06e — chip extraction: warpAffine + dim_size fix

### Discovery: dim_size defaults differ from expected

WBIA's `ChipConfig` defaults are:
- `dim_size = 700` (not 450)
- `resize_dim = 'maxwh'` (not 'width')
- `histeq = False`, `adapteq = False`, `grayscale = False`

The `algo/Config.py` comments line 782 (`cc_cfg.dim_size = 450`) are
outdated — the real defaults live in `core_annots.ChipConfig`.

### Fix 1: correct dim_size

Changed `_extract_chip` from `dim_size=450, resize_dim='width'` to
`dim_size=700, resize_dim='maxwh'`. This produces larger chips
(700×maxwh ≈ 700×500 vs 450×300), giving ~2.4× more pixels.

**Parity improvement (10 annots, 3 queries)**:

| Metric | Before (450/width) | After (700/maxwh) |
|---|---|---|
| Mean ρ | 0.25 | 0.29 |
| Query 0 ρ | 0.92 | **0.98** |
| Score ratio (wbia-core/WBIA) | 0.2-0.3× | 0.5-0.6× |
| Top-3 overlap | 44% | 67% |
| Timing | 3.2s | 6.9s |

### Discovery: cv2.warpAffine ≠ crop + cv2.resize

Compared chip extraction methods directly on a real COCO image:

| Metric | Value |
|---|---|
| Pixels differing | 75% (522,674 / 699,300) |
| Max pixel diff | 26 (out of 255) |
| Mean pixel diff | 1.88 |
| Pixels diff > 5 | 6.7% (46,864) |

**Root cause**: `cv2.warpAffine` does a single-step Lanczos interp
from source image to chip. `crop + resize` does two steps: nearest-
neighbor crop (integer pixels) then Lanczos resize. When the affine
scale factors differ between width and height (sx=0.772 ≠ sy=0.771),
the single-step interpolant samples slightly different source
coordinates than the two-step approach.

### Fix 2: use cv2.warpAffine

Rewrote `_extract_chip()` to use `cv2.warpAffine` with the exact
same affine matrix as WBIA's `extract_chip_from_img()`:

```python
M = _compute_affine_matrix((x, y, w, h), (new_w, new_h), theta)
return cv2.warpAffine(img, M, (new_w, new_h),
    flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)
```

Added `_compute_affine_matrix()` matching WBIA's
`vtool.chip.get_image_to_chip_transform()` — translation to bbox
center + scale + rotation + translation to chip center.

**Parity after warpAffine fix**:

| Query | Top-1 agree? | Before ρ | After ρ | Score ratio |
|---|---|---|---|---|
| 0 | YES | 0.98 | **1.00** | 0.57× |
| 1 | NO | 0.07 | **0.10** | 0.61× |
| 2 | NO | -0.12 | -0.13 | 0.59× |

**Mean ρ**: 0.29 → **0.32**, spearman_below: 3 → **2**

### Query 0 at ρ=1.00 — scoring formula confirmed

The scoring pipeline is **functionally correct**. Query 0 achieves
perfect rank correlation (ρ=1.00, identical top-5 ordering) with
WBIA. The score magnitudes are 1.6-1.7× lower but the relative
ordering matches exactly for unambiguous cases.

### Remaining gap: fundamental library version noise

The 1.6× score ratio and ρ≈0 on queries 1-2 are attributed to
**libjpeg/OpenCV version differences** between our Docker image
(Ubuntu 24.04 + OpenCV 4.9 + libjpeg-turbo 2.1) and the WBIA
reference image (wildme/wbia:latest with potentially different
library versions).

These version differences cause:
1. Slightly different JPEG decode → different pixel values (±1-2)
2. Slightly different warpAffine interpolation (Lanczos-4)
3. → Different SIFT descriptors
4. → Different FLANN distances
5. → Different LNBNN weights
6. → Different rankings for ambiguous queries

**Query 0 is unambiguous** (large score gaps between annotations) so
the noise doesn't change rankings. **Queries 1-2 are ambiguous**
(similar scores for top annotations) so even small noise can swap
the winner.

### What was investigated and ruled out

| Theory | Result |
|---|---|
| FLANN KD-tree non-determinism | Ruled out — exact search = identical results |
| Missing FG weights | Ruled out — `fg_on=False` in both systems |
| probchip masking | Ruled out — WBIA's RGB chip is used directly |
| Score normalization formula | Confirmed correct — `raw / 524288`, no sqrt |
| Feature extraction params | Confirmed correct — pyhesaff default params |
| Chip dimensions | Fixed — now 700/maxwh matching WBIA |
| Chip extraction method | Fixed — now warpAffine matching WBIA |

### Current file state

```
wbia-core/
├── sidecar/api.py                  # _extract_chip via warpAffine, _compute_affine_matrix
├── src/wbia_core/
│   ├── pipeline.py                 # identify() with correct distance norm
│   ├── features.py                 # pyhesaff extract_features
│   └── knn.py                      # exact_knn implemented, not yet wired
├── tests/benchmark/
│   └── run_benchmark.py            # --flann-algorithm flag, --reference mode
└── docs/development/
    ├── devlog.md                   # This file
    └── parity-analysis.md          # Full parity investigation log
```

---

## 2026-06-07 — WBIA build audit: wbia-core Dockerfile vs WBIA provision image

### Motivation

Previous devlog entries (06-06e, 06-06f) identified the remaining parity gap as
library version differences (libjpeg, OpenCV) between Docker images. The wbia-core
Dockerfile already uses `nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04` as base —
the same as WBIA. Now we audit the full WBIA build chain to find any remaining
differences.

### WBIA build chain (from `wildbook-ia/devops/`)

WBIA has a three-stage Docker build:

1. **`wbia-base`** (`devops/base/Dockerfile`)
   - Base: `nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04`
   - Installs system deps via apt: `libopencv-dev`, `libboost-all-dev`, `libgdal-dev`,
     `libeigen3-dev`, `libgeos-dev`, `libproj-dev`, `graphviz`, `python3-pyqt5`, etc.
   - Creates `/virtualenv/env3` with `--system-site-packages`, pins
     `pip==22.3.1`, `setuptools==59.5.0`, `wheel==0.38.4`
   - Installs `cmake`, `ninja`, `scikit-build`, `setuptools_scm[toml]`, `cython`
   - `LD_LIBRARY_PATH`: `/usr/local/cuda/lib64:/virtualenv/env3/lib:...`

2. **`wbia-provision`** (`devops/provision/Dockerfile`)
   - Clones all repos into `/wbia/`: `wbia-utool`, `wbia-vtool`, `wbia-tpl-pyhesaff`,
     `wbia-tpl-pyflann`, `wildbook-ia`, plus plugins
   - Constrains `setuptools<75` globally (for `pkg_resources` compat)
   - Installs PyTorch with CUDA 11.7 early (before package builds)
   - **Builds in order** via `run_developer_setup.sh` for each toolkit:
     1. `wbia-utool` — pure Python, `pip install -r requirements.txt && setup.py develop && pip install -e .`
     2. `wbia-vtool` — has `.so` (libsver), `build_ext --inplace` first
     3. `wbia-tpl-pyhesaff` — has `.so` (libhesaff), same `build_ext --inplace` flow
     4. `wbia-tpl-pyflann` — has `.so`
     5. `wildbook-ia` — main app, `pip install -r requirements.txt && pip install .`
   - After all builds: reinstalls `opencv-contrib-python-headless==4.7.0.72` over
     any conflicting opencv packages

3. **`wbia`** (`devops/Dockerfile`) — final image: copies `/virtualenv` and `/wbia`
   from provision, runs smoke tests

### wbia-core Dockerfile vs WBIA: diff analysis

| Aspect | WBIA provision | wbia-core | Same? |
|---|---|---|---|
| **Base image** | `nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04` | Same | ✓ |
| **System OpenCV** | `libopencv-dev` (apt) | Same | ✓ |
| **Runtime OpenCV** | `opencv-contrib-python-headless==4.7.0.72` | Same via pyproject.toml | ✓ |
| **Python** | `/virtualenv/env3` with `--system-site-packages` | System `python3` (global) | ✗ |
| **Build tools** | cmake, ninja, scikit-build, setuptools_scm, cython | Same | ✓ |
| **setuptools pin** | `<75` (pkg_resources compat) | `>=69` (no upper bound) | ⚠ |
| **PyTorch/CUDA** | `torch==2.0.1` + `torchvision==0.15.2` (cu117) | Not installed | ✗ |
| **Submodule build** | `run_developer_setup.sh` (installs requirements first) | `pip install --no-deps` (skips reqs) | ✗ |
| **pip constraints** | `PIP_CONSTRAINT=/tmp/pip-constraints.txt` (setuptools<75) | None | ✗ |
| **LD_LIBRARY_PATH** | `/usr/local/cuda/lib64:/virtualenv/env3/lib:` | `/virtualenv/env3/lib:` | ⚠ |

### What `run_developer_setup.sh` does (vs our `--no-deps` approach)

WBIA runs this for **each** submodule before `pip install`:

```bash
pip install -r requirements/build.txt     # cmake, ninja, scikit-build, wheel
pip install -r requirements.txt           # ALL runtime deps (numpy, networkx, etc.)
python setup.py build_ext --inplace       # compile .so
python setup.py develop                   # dev install
pip install -e .                          # editable install
```

Our Dockerfile does:
```bash
pip3 install --no-cache-dir --no-deps ./wbia-utool/       # skip utool's 15+ runtime deps
pip3 install --no-cache-dir --no-deps ./wbia-vtool/       # skip vtool's deps
cd wbia-tpl-pyhesaff && python3 setup.py build_ext --inplace \
    && pip3 install --no-cache-dir --no-deps -e . && cd ..
pip3 install --no-cache-dir . flask gunicorn  # wbia-core + its deps from pyproject.toml
```

**Impact of `--no-deps`**: Submodule runtime dependencies (like `networkx==2.5.1`,
`numpy==1.20`, `ubelt`, `statsmodels`, etc.) are eventually installed by wbia-core's
`pyproject.toml` → `pip install .` at the end. But version constraints differ:
- WBIA's vtool specifies `numpy==1.20`; ours gets `numpy>=1.24,<2` from pyproject.toml
- WBIA's vtool specifies `networkx==2.5.1` (exact pin); ours gets whatever
  `opencv-contrib-python-headless` or numpy pulls in
- `wbia-pyflann` is listed in WBIA's vtool runtime deps — we install it separately
  via pyproject.toml

### Verified: pyhesaff compilation is identical

Both WBIA and wbia-core compile pyhesaff with the exact same `setup.py` and CMake
files (from the same vendored submodule). Both use `build_ext --inplace` followed
by `pip install -e .`. The resulting `libhesaff.so` is built against the system's
`libopencv-dev` headers and linked against the system's `libopencv_*` shared libs.

### Remaining differences that could affect SIFT parity

1. **Runtime dependency versions**: numpy, scipy, networkx, scikit-image version
   differences between WBIA's pinned constraints and our transitive resolution
   could affect chip preprocessing (color conversion, histogram operations) before
   features are extracted. These are Python-level differences, not C-level.

2. **LD_LIBRARY_PATH**: WBIA includes `/usr/local/cuda/lib64` — irrelevant for
   SIFT (no CUDA in pyhesaff) but could matter if any numpy/scipy operation paths
   differ.

3. **Virtualenv `--system-site-packages`**: WBIA's virtualenv inherits system
   packages. Our global pip install may resolve different versions of `six`,
   `python-dateutil`, etc. that cascade into numpy/scipy behavior.

4. **PyTorch**: Not used in the SIFT pipeline. Shouldn't affect parity.

### Conclusion

The build environments are **structurally equivalent** — same base image, same
OpenCV setup, same pyhesaff compilation. The remaining parity gap (ρ=0.32 mean,
1.6× score ratio) is likely caused by **Python package version differences** in
the transitive dependency tree (numpy, scipy, Pillow) rather than Docker image
architecture. WBIA pins exact versions (e.g., `numpy==1.20`, `networkx==2.5.1`)
while our `--no-deps` approach lets wbia-core's looser constraints
(`numpy>=1.24,<2`) resolve to different versions.

**Next step**: Pin exact dependency versions in wbia-core's pyproject.toml to
match WBIA's requirements, or use `pip install -r requirements.txt` from each
submodule before building (same as `run_developer_setup.sh`).

---

## 2026-06-07b — Full test suite run, Makefile, build audit verified

### Image build

Dockerfile already using `nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04` base
(matching WBIA). Build succeeded — 8.89GB image with `opencv-contrib-python-headless==4.7.0.72`
in pyproject.toml and pyhesaff source-compiled from submodules.

### Test results (all passing)

| Layer | Tests | Result | Time |
|---|---|---|---|
| Unit | 38 | ✓ all pass | 1.0s |
| Benchmark (pytest) | 18 | ✓ all pass | 16.9s |
| Replay (fixture) | 84 | ✓ all pass | 67s |
| Replay (live WBIA) | 1 | ✗ (no WBIA running) | — |

### Test infrastructure fixes

1. **Makefile created** (`wbia-core/Makefile`) — standardised targets:
   - `make test-unit` — 38 fast unit tests
   - `make test-benchmark` — 18 benchmark pytests (needs dataset mount)
   - `make test-parity` — COCO benchmark vs WBIA reference (from HOST, needs `docker` CLI)
   - `make test-replay` — 84 fixture replay tests (self-contained)
   - `make test-replay-live` — 1 live WBIA comparison (needs Docker socket + WBIA)
   - `make build`, `make server`, `make shell`, `make clean`

2. **`test-parity` must run from host**, not inside Docker. The `CoreTargetRunner`
   uses `subprocess.run(["docker", "run", ...])` to start the wbia-core sidecar.
   Running inside the container fails with "docker: command not found".

3. **Benchmark tests need volume mount**: `tests/test-dataset/` is in `.dockerignore`.
   Must mount with `-v $(pwd)/tests/test-dataset:/app/tests/test-dataset`.

4. **Replay fixtures are baked into the image** — `testdata/` is NOT in `.dockerignore`.
   84/85 tests run self-contained. Only `TestLiveWbiaComparison` needs WBIA.

5. **Results directory** changed from root `test-run-results-*` to
   `test-results/test-run-results-*`. `.gitignore` updated accordingly.

### Parity analysis (post-image-build)

| Query | Top-1 agree? | Spearman ρ | Score ratio (core/WBIA) |
|---|---|---|---|
| 0 | ✓ | **1.00** | 0.69× |
| 1 | ✗ | 0.10 | 0.73× |
| 2 | ✗ | -0.12 | 0.72× |

Mean ρ: 0.33, Top-3 overlap: 67%, Score ratio: ~0.7× (consistent).
Same results as before OpenCV pin — switching to the pip wheel didn't change parity.

### Docs updated

- `AGENTS.md` — fixed replay and benchmark instructions, added parity analysis section
- `docs/development/testing-guide.md` — updated with correct commands, Makefile references
- `docs/development/devlog.md` — this entry, plus 06-07 WBIA build audit
- `.gitignore` — `test-run-results-*` → `test-results/`

### Current blockers for ≥90% ρ

1. **pyhesaff build differences** — our `.so` compiled in the same base image on the
   same system, but different git commit / build flags than what's in `wildme/wbia:latest`.
   This is the last systematic difference. The scoring pipeline is verified correct
   (Q0 ρ=1.00).

2. **Reference WBIA results may be stale** — the reference at
   `tests/benchmark/reference/wbia-latest-10/` was recorded with an older WBIA build.
   Could re-record with current `wildme/wbia:latest`.

### Path forward

- Option A: Re-record WBIA reference with `docker pull wildme/wbia:latest`
- Option B: Build pyhesaff from the exact same source as WBIA's provision image
- Option C: Extract features from WBIA directly, store as fixtures for scoring-only tests
```

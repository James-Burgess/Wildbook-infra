# wbia-core Development Log

This file tracks design decisions, progress, and open questions as the
package evolves.  It complements the formal ADRs in `decisions/`.

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

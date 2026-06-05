# wbia-core

`wbia-core` is a pure-Python pip package that contains the algorithmic primitives for wildlife re-identification. It is the first of the three new layers in the modernization plan; see [architecture](architecture) for context.

## What it is

A modern replacement for the algorithmic half of `wildbook-ia`. Where `wbia.algo.hots` is a 3000-line module that talks to `IBEISController`, reads from a SQLite depcache, and is loaded by a plugin-injection framework, `wbia-core` is a flat library of plain functions over numpy arrays.

- No `IBEISController`. No class-method injection. No `__init__` magic.
- No DB. No network. No logging side effects (only `WARNING`+ to stdout).
- No state. Functions are pure: same `(image_bytes, config)` → same numpy arrays.
- Bit-exact determinism. Same config + same image = same features, every time, on every machine. This is testable and enforced by the test suite.
- Modern Python 3.11+ type hints throughout. `numpy` arrays are typed as `npt.NDArray[np.float32]`. Pydantic v2 models for the config objects.

## What it replaces

| `wildbook-ia` module | Lines | Replaced by `wbia-core` module |
|---|---|---|
| `wbia.algo.hots.chip_match` | 3039 | `wbia_core.feature_set`, `wbia_core.match` |
| `wbia.algo.hots.pipeline` | ~250 | `wbia_core.pipeline.identify` (one function) |
| `wbia.algo.hots.query_request` | 1369 | `wbia_core.config.HotSpotterConfig` (Pydantic model) |
| `wbia.algo.hots.nn_weights` | ~150 | `wbia_core.scoring.lnbnn_score` |
| `wbia.algo.hots.scoring` | ~200 | `wbia_core.scoring` |
| `wbia.algo.hots.match_chips4` | ~600 | `wbia_core.pipeline` |
| `wbia.algo.hots.spatial_verification` (inline in `pipeline.py`) | ~150 | `wbia_core.spatial_verify` |
| `wbia.algo.hots.neighbor_index` + `neighbor_index_cache` | ~400 | `wbia_core.knn` (no caching; the caller is `wildlife-id`) |
| `wbia.algo.hots.name_scoring` | ~100 | `wbia_core.scoring.name_aggregate` |
| `wbia.algo.hots.exceptions` | ~50 | `wbia_core.exceptions` (much smaller) |

What it does **not** replace (those stay in `wildlife-id` or in Wildbook's Java side):

- The IBEISController, the depcache, the ZMQ job engine, the Gunicorn web layer, the `manual_*.py` plugins, the `wbia.constants` lookup tables, the species/occurrence/image management UI, the bulk-import paths. None of those are algorithmic primitives.

## Source extraction strategy

The starting point is `cp -r wbia/algo/hots wbia-core/wbia_core/` and then delete everything that doesn't belong. Specifically:

1. Delete every line that imports from `wbia.utool`, `wbia.dtool`, `wbia.constants`, `wbia.control`, or `wbia.algo.hots.preproc`.
2. Replace `ut.inject_instance` and `ut.util_class.inject` calls with plain function args.
3. Replace the `@register_preproc` decorator pattern with explicit function calls.
4. Replace `ut.partial` and the dynamic `setattr` patterns with explicit dataclass fields.
5. Replace the `wbia.constants` lookup tables (PATH_DEFAULTS, KEY_DEFAULTS, etc.) with Pydantic config models.
6. Replace the SQLite-backed `neighbor_index_cache` with a stateless `wbia_core.knn.knn_match(query, database, k)` function.
7. Replace the `ChipMatch` class (which inherits from `ut.util_class.InjectedMetaclass`) with `@dataclass(frozen=True)` data containers.

The result should be ~2000-3000 lines, no `ut.` references, and a clean public API.

## Public API

The package exports a small, versioned set of functions and config models. Everything else is internal.

### Config models (Pydantic v2)

```python
import wbia_core

# HotSpotter feature extraction (SIFT-based, Hessian-affine keypoints)
hs_config = wbia_core.HotSpotterConfig(
    feature_type="hotspotter",
    model_version="1.0.0",
    sift_n_features=1000,
    hessian_threshold=0.0001,
    nms_radius=8,
    sift_contrast_threshold=0.04,
    sift_edge_threshold=10.0,
)

# MiewID embedding extraction (CNN-based, v4.1)
miewid_config = wbia_core.MiewIdConfig(
    feature_type="miewid-embedding",
    model_id="miewid-msv4.1",
    version="4.1",
    image_size=440,
    normalize=True,
    embedding_dim=512,
)

# Identification pipeline (HotSpotter LNBNN + spatial verification)
id_config = wbia_core.IdentificationConfig(
    feature_type="hotspotter",
    k_neighbors=50,
    lnbnn_alpha=0.5,
    lnbnn_n=3,
    spatial_verify=True,
    spatial_inlier_threshold=0.15,
    score_method="nsum",
)
```

Every config model has a `config_hash` property that returns a SHA-256 hex digest of its serialized form. This is the version identifier used by `wildlife-id` to validate that the running config matches the index.

### Data containers

```python
# A set of features extracted from a single image (or region)
features: wbia_core.FeatureSet = wbia_core.extract_features(...)

# features.keypoints: np.ndarray [N, 2] float32  (x, y)
# features.descriptors: np.ndarray [N, 128] uint8  (SIFT)
# features.image_size: tuple[int, int]  (width, height)
# features.config_hash: str  (SHA-256)
# features.weights_hash: str  (SHA-256 of model weights)

# A match between a query feature and a database feature
match: wbia_core.Match = ...

# match.query_idx: int
# match.db_idx: int  (index into the database list passed to knn_match)
# match.db_aid: str  (annotation id of the database annotation)
# match.distance: float

# A scored + re-ranked match
scored: wbia_core.ScoredMatch = ...

# scored.db_aid: str
# scored.score: float
# scored.rank: int
# scored.evidence: dict  (debug info: inlier count, kp match count, etc.)
```

### Functions

```python
def extract_features(
    image_bytes: bytes,
    config: HotSpotterConfig | MiewIdConfig,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    theta: float = 0.0,
) -> FeatureSet:
    """Extract features from an image or region.

    `bbox` is (x, y, w, h) in pixel coordinates of the original image.
    `theta` is rotation in radians. The function rotates the image by
    -theta before cropping, matching the wbia-plugin-miew-id convention.
    """

def extract_embedding(
    image_bytes: bytes,
    config: MiewIdConfig,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    theta: float = 0.0,
) -> npt.NDArray[np.float32]:
    """Extract a single embedding vector. Returns shape [D] float32."""

def knn_match(
    query: FeatureSet,
    database: list[FeatureSet],
    *,
    k: int = 50,
    backend: str = "auto",  # "auto" | "faiss" | "flann"
) -> list[Match]:
    """Find the k-nearest neighbors of `query` in `database`.

    `backend="auto"` picks the best available implementation:
    faiss-cpu if installed, else wbia-pyflann.

    Returns at most k matches per query feature, sorted by distance.
    """

def score_matches(
    matches: list[Match],
    *,
    method: Literal["lnbnn", "lnn", "nsum"] = "lnbnn",
    alpha: float = 0.5,
    n: int = 3,
) -> list[ScoredMatch]:
    """Score the matches using LNBNN or a related method.

    LNBNN (Local Naive Bayes Nearest Neighbor) is the default. See
    `wbia_core.scoring.lnbnn_score` for the formula.
    """

def spatial_verify(
    query: FeatureSet,
    candidates: list[ScoredMatch],
    database: list[FeatureSet],
    *,
    config: IdentificationConfig,
) -> list[ScoredMatch]:
    """Re-rank candidates by spatial consistency of feature matches.

    Returns the input list re-sorted (highest score first) with the
    `evidence` field populated for each ScoredMatch.
    """

def identify(
    query_image_bytes: bytes,
    database: list[tuple[str, FeatureSet]],  # (aid, features)
    *,
    extraction_config: HotSpotterConfig | MiewIdConfig,
    identification_config: IdentificationConfig,
) -> list[ScoredMatch]:
    """Convenience: extract features from the query, run the full pipeline.

    Returns the top-K candidates sorted by score, where K is determined
    by `identification_config.k_neighbors`.
    """
```

The full list of public symbols lives in `wbia_core/__init__.py`. Anything not exported is internal and may change without notice.

## Determinism contract

This is the most important contract of `wbia-core`. The package is **bit-exact deterministic** by default:

- Same `(image_bytes, config)` → same `FeatureSet.keypoints` and `FeatureSet.descriptors`, every time, on every machine.
- Same `(query, database, k)` → same list of `Match` objects, every time.
- The same property holds for `score_matches`, `spatial_verify`, and `identify`.

This is enforced by the test suite. Tests run with fixed numpy/torch/cuDNN versions and `torch.use_deterministic_algorithms(True)`. CUDA tests use a fixed seed and assert bitwise equality.

The hashes are used to validate the index in `wildlife-id`:

- `config_hash` — SHA-256 of the serialized config (Pydantic `model_dump_json()`).
- `weights_hash` — SHA-256 of the model weights file. For HotSpotter this is the SIFT codebook (or `none` if no codebook is used). For MiewID this is the `.bin` checkpoint.

If you change the algorithm, the `model_version` field changes, and the `config_hash` changes. Old indices are invalidated. This is the desired behavior: silent algorithmic drift is worse than a forced re-index.

## Dependencies

```text
# requirements.txt
numpy>=1.26
opencv-python-headless>=4.8
torch>=2.1
pydantic>=2.6
faiss-cpu>=1.7.4
# Optional fallback if faiss is unavailable
wbia-pyflann>=1.6.14
# Used for Hessian-affine keypoint extraction
wbia-pyhesaff>=1.2
```

The package does **not** depend on `wbia.utool`, `wbia.vtool`, `wbia.dtool`, `wbia.constants`, or any other `wbia.*` package except `wbia-pyflann` and `wbia-pyhesaff` (which are standalone).

`faiss-cpu` replaces the legacy `wbia-pyflann` dependency. It has a much better API, is actively maintained, and supports GPU indexing (out of scope for v1 but available). If `faiss-cpu` is not installed, the package falls back to `wbia-pyflann` for backward compat.

## Testing

The test suite has three layers:

### Unit tests (fast, < 30s)

Located in `wbia-core/tests/unit/`. Cover each function in isolation against small synthetic inputs. The MiewID tests use a tiny mock model (1-layer CNN, 8-dim output) so they run on CPU in milliseconds.

### Determinism tests (slow, ~5min)

Located in `wbia-core/tests/determinism/`. Run the full pipeline against 100 fixed image fixtures and assert that the output is bit-exact reproducible. The fixtures are checked into the repo. Any change to the algorithm MUST update the fixtures and the expected outputs. The CI runs these on every PR; a failure is a blocker.

### Parity tests (slow, ~30min)

Located in `wbia-core/tests/parity/`. Run the full pipeline against the same images and configs that the legacy `wildbook-ia` test suite uses, and assert that the output matches the legacy output within tolerance (≤ 1e-6 for SIFT descriptors, ≤ 1e-5 for LNBNN scores, ≤ 1e-4 for spatial verification scores). The legacy test fixtures are imported from `wildbook-ia/tests/` (read-only).

Parity tests are the critical proof that `wbia-core` is algorithmically equivalent to `wildbook-ia`'s HotSpotter pipeline. If parity tests pass, you can swap `wbia-core` for `wbia.algo.hots` without changing the identification results.

## Repository layout

```text
wbia-core/
├── README.md
├── LICENSE                                (MIT)
├── pyproject.toml
├── requirements.txt
├── src/
│   └── wbia_core/
│       ├── __init__.py                    (public API)
│       ├── _version.py
│       ├── config.py                      (Pydantic config models)
│       ├── features.py                    (extract_features, extract_embedding)
│       ├── knn.py                         (knn_match)
│       ├── scoring.py                     (lnbnn_score, score_matches)
│       ├── spatial.py                     (spatial_verify)
│       ├── pipeline.py                    (identify)
│       ├── data.py                        (FeatureSet, Match, ScoredMatch dataclasses)
│       ├── exceptions.py
│       └── _internal/
│           ├── sift.py                    (vendored from wbia-pyhesaff)
│           ├── hessian.py
│           ├── flann_backend.py
│           └── faiss_backend.py
├── tests/
│   ├── unit/
│   ├── determinism/
│   │   ├── fixtures/                      (100 fixed images)
│   │   └── test_determinism.py
│   └── parity/
│       └── test_parity.py
└── docs/
    ├── api.md
    ├── algorithm.md
    └── determinism.md
```

## Build and publish

```bash
# Local development
cd wbia-core
pip install -e ".[dev]"
pytest tests/unit -x
pytest tests/determinism -x
pytest tests/parity -x

# Publish to PyPI
python -m build
twine upload dist/*
```

The package is published to PyPI as `wbia-core` (MIT license). The `wildlife-id` service depends on it as `wbia-core>=1.0,<2.0`. Versioning follows semver: breaking changes bump the major.

## What is explicitly NOT in `wbia-core`

- **No I/O outside of the function args.** `wbia-core` does not read from disk, does not write to disk, does not connect to a network. The `image_bytes: bytes` arg is the only way to feed it an image.
- **No `IBEISController` or anything that resembles it.** There is no class to instantiate, no `__init__` to call, no global state. The functions are all module-level.
- **No `wbia.utool` or `wbia.vtool` or `wbia.dtool`.** Those are part of the legacy `wildbook-ia` package and are not imported here.
- **No `wbia.constants` lookup tables.** Configuration is via Pydantic models with explicit fields. There is no global "PATH_DEFAULTS" or "KEY_DEFAULTS" dict.
- **No `wbia.algo.hots.preproc` integration.** Preprocessors (chip extraction, occurrence extraction, etc.) are the caller's responsibility. The `extract_features` function takes an optional `bbox` arg and handles the chip extraction itself.
- **No `wbia.algo.graph`.** The knowledge-graph review UI lives in `wildbook`'s Java code, not in `wbia-core`.
- **No `wbia.algo.smk`.** The Selective Match Kernel experimental pipeline is deprecated. Not ported.
- **No `wbia.algo.detect`.** Detection is ml-service's job as of 10.10. Not ported.

## Why this is the right cut

`wbia-core` is the smallest unit of work that, if you have it, proves the algorithm is preserved. The test target is straightforward: pin the inputs, pin the config, assert the output is bit-exact. No service to spin up, no DB to seed, no Wildbook to install. Once `wbia-core` exists and its tests pass, the rest of the modernization plan is mechanical.

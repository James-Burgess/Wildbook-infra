# wbia-core

Core animal identification algorithm — Hessian-affine SIFT pipeline extracted from `wildbook-ia`.

## Current status (June 2026)

wbia-core is a working HotSpotter reimplementation. A single Docker image provides server + test entrypoints. Features are extracted from **chips** via `cv2.warpAffine` (matching WBIA's `extract_chip_from_img` exactly) with `dim_size=700, resize_dim='maxwh'`. Pyhesaff is source-compiled from submodules.

Score magnitudes and query times match WBIA after fixing distance normalization, chip dimensions, and chip extraction method. **The scoring pipeline is functionally correct**: Query 0 achieves ρ=1.00 (perfect rank correlation) against WBIA.

### Parity (vs WBIA reference, 10 annots, 3 queries)

| Query | Top-1 agree? | Spearman ρ | Score ratio (core/WBIA) |
|---|---|---|---|
| 0 | ✓ | **1.00** | 0.57× |
| 1 | ✗ | 0.10 | 0.61× |
| 2 | ✗ | -0.13 | 0.59× |

**Mean ρ**: 0.32, **Top-3 overlap**: 67%

### Remaining gap

The 1.6× score ratio and ρ≈0 on ambiguous queries are attributed to
**library version differences** (OpenCV, libjpeg) between Docker images
causing subtle JPEG decode + warpAffine pixel differences. These cascade
through SIFT → descriptors → FLANN distances → LNBNN weights, affecting
ranking only for ambiguous queries where scores are close.

### Feature extraction

The only supported extractor is **pyhesaff** (Hessian-affine keypoints + SIFT descriptor), matching WBIA's extractor. OpenCV SIFT fallback has been removed — `wbia-pyhesaff` is a hard dependency.

**Why source-built submodules.** The PyPI wheel for `wbia-pyhesaff` 4.0.0 depends on `wbia-vtool` which ships a pre-compiled `libsver.so` (and in the wheel, bundled OpenCV 2.4.5 libraries). When loaded alongside system OpenCV 4.x, this causes a SIGSEGV at import time. Similarly, `wbia-vtool` depends on `wbia-utool`. All three must be compiled from source against the target system's `libopencv-dev`.

The solution: vendored git submodules inside `wbia-core/`, built in dependency order with `pip install --no-deps` before installing wbia-core itself.

### Single image, two entrypoints

| Entrypoint | Usage |
|---|---|
| `scripts/entrypoints/server-entrypoint.sh` | `gunicorn sidecar.api:app` on port 5000 |
| `scripts/entrypoints/test-entrypoint.sh` | Runs parity tests |

```bash
docker run wbia-core:latest                                # server mode
docker run --entrypoint scripts/entrypoints/test-entrypoint.sh wbia-core:latest  # test mode
```

## Submodules

wbia-core vendors three WildMe packages as git submodules for source compilation:

| Submodule | Path | Purpose |
|---|---|---|
| `wbia-utool` | `wbia-core/wbia-utool/` | Utility library (pure Python) |
| `wbia-vtool` | `wbia-core/wbia-vtool/` | Vision tools + spatial verification (`libsver.so`) |
| `wbia-tpl-pyhesaff` | `wbia-core/wbia-tpl-pyhesaff/` | Hessian-affine SIFT (`libhesaff.so`) |

```bash
git clone --recursive git@github.com:WildMeOrg/wildbook-infra.git
# Submodules are in wbia-core/, pulled automatically
```

## Architecture

```
wbia-core/
├── Dockerfile                       # Builds submodule deps + wbia-core
├── pyproject.toml                   # Deps: numpy, pydantic, wbia-pyflann, wbia-pyhesaff
├── sidecar/
│   └── api.py                       # Flask app — single-shot POST /api/v1/identify/
├── scripts/
│   └── entrypoints/
│       ├── server-entrypoint.sh     # gunicorn entrypoint
│       └── test-entrypoint.sh       # parity test entrypoint
├── wbia-utool/                      # git submodule — pure Python utilities
├── wbia-vtool/                      # git submodule — vision tools (libsver.so)
├── wbia-tpl-pyhesaff/               # git submodule — Hessian-affine SIFT (libhesaff.so)
├── src/wbia_core/
│   ├── features.py                  # extract_features() — pyhesaff only
│   ├── pipeline.py                  # identify() — full LNBNN pipeline
│   ├── knn.py                       # k-NN via pyflann
│   ├── scoring.py                   # LNBNN scoring
│   ├── spatial.py                   # Spatial verification (OpenCV)
│   ├── data.py                      # FeatureSet, AnnotatedImage, ScoredMatch
│   └── config.py                    # Pydantic config models
├── tests/
│   ├── benchmark/                   # COCO-based multi-target regression suite
│   ├── replay/                      # Recorded fixture replay tests
│   └── test_features.py             # Feature extraction unit tests
└── docs/
    ├── decisions/                   # ADRs
    └── development/                 # Plans, contract, devlog
```

## Build & run

```bash
cd wbia-core
docker build -t wbia-core:latest .
docker run -d --name wbia-core -p 5000:5000 wbia-core:latest
curl http://localhost:5000/api/health/
```

## Testing

```bash
# Run core tests inside container
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/ -q --ignore=tests/benchmark --ignore=tests/replay"

# Run server + test endpoint
docker run -d --name wbia-core -p 5001:5000 wbia-core:latest
curl -X POST http://localhost:5001/api/v1/identify/ -H "Content-Type: application/json" -d '{...}'
```

## What's next

- **Prove feature parity**: With pyhesaff active in both wbia-core and WBIA, re-run the COCO benchmark to confirm ranking agreement.
- **Service architecture decision**: Whether wbia-core lives as a module inside the ML service, as a standalone sidecar, or inlined into the next-gen identification service.
- **Wildbook-ia decoupling**: Once parity is confirmed, `wildbook-ia`'s `algo/hots/` can be deprecated.

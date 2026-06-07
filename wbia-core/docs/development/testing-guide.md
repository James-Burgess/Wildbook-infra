# wbia-core Testing Guide

## Overview

wbia-core has four testing layers:

| Layer | Scope | Speed | CI | Command |
|---|---|---|---|---|
| **Unit** | Pure functions, config, data containers | < 2s | Always | `pytest tests/ --ignore=tests/benchmark --ignore=tests/replay` |
| **Benchmark** | COCO wildlife dataset, multi-target regression | 5–60 min | On demand | `python tests/benchmark/run_benchmark.py` |
| **Replay** | Recorded WBIA fixtures, parity verification | ~1 min | Self-contained | `pytest tests/replay/ -k 'not TestLiveWbiaComparison'` |
| **Server** | Flask sidecar health + identify endpoints | < 1s | Always | `pytest tests/benchmark/sidecar/test_sidecar.py` |

---

## Layer 1: Unit Tests

Tests individual algorithmic functions against synthetic inputs. No Docker, no network, no WBIA.

**Location:** `tests/`

```
tests/
├── test_features.py    # extract_features() with pyhesaff
├── test_config.py      # Pydantic config models (8 tests)
├── test_data.py        # FeatureSet, AnnotatedImage, ScoredMatch (7 tests)
├── test_knn.py         # FLANN k-NN matching (2 tests)
├── test_pipeline.py    # Full identify() pipeline (12 tests)
├── test_scoring.py     # LNBNN scoring (7 tests)
└── test_spatial.py     # Spatial verification (3 tests)
```

### Run

```bash
# Inside Docker container
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/ --ignore=tests/benchmark --ignore=tests/replay -v"

# Or on host with venv
cd wbia-core
pip install -e ".[dev]"
pytest tests/ --ignore=tests/benchmark --ignore=tests/replay -v
```

**Results:** 40+ tests in < 2 seconds.

### What they don't cover

- Feature extraction correctness (requires pyhesaff + real images)
- WBIA parity (requires WBIA comparison)
- Real-world performance (synthetic descriptors are tiny)

---

## Layer 2: COCO Benchmark Tests

Multi-target regression suite using a real-world wildlife COCO dataset (4,948 images, 6,925 annotations, giraffe+zebra). Runs subsets through multiple identification backends and compares rankings.

**Location:** `tests/benchmark/`

```
benchmark/
├── run_benchmark.py    # CLI driver
├── runner.py           # Orchestrator — starts targets, runs queries, saves results
├── compare.py          # Cross-target comparator (Spearman ρ, top-k overlap, score delta)
├── analyze.py          # Result analysis CLI (report, fixtures, check)
├── coco/
│   ├── loader.py       # COCO dataset loader with deterministic subset selection
│   └── test_loader.py  # Loader unit tests (7 tests)
├── targets/
│   ├── base.py         # TargetConfig, TargetRunner, QueryResult
│   ├── core.py         # CoreTargetRunner — single-shot POST to wbia-core sidecar
│   ├── wbia.py         # WbiaTargetRunner — multi-step WBIA REST flow
│   └── test_runners.py # Runner tests (3 tests, require Docker)
├── sidecar/
│   └── test_sidecar.py # Flask app endpoint tests (2 tests)
├── test_runner.py      # Benchmark runner integration tests (2 tests)
└── conftest.py         # Shared fixtures
```

### Targets

| Key | Image | Description |
|---|---|---|
| `wbia-core` | `wbia-core:latest` | Single-shot identify via Flask sidecar |
| `wbia-latest` | `wildme/wbia:latest` | Full WBIA pipeline (latest stable) |
| `wbia-nightly` | `wildme/wbia:nightly` | Full WBIA pipeline (nightly build) |
| `wbia-develop` | `wildme/wbia:develop` | Full WBIA pipeline (dev branch) |

### CLI

```bash
# Full benchmark (reference WBIA results, no WBIA container needed)
# MUST run from host — uses docker CLI to start wbia-core sidecar
python3 tests/benchmark/run_benchmark.py \
    --n-annots 10 --n-queries 3 \
    --reference tests/benchmark/reference/wbia-latest-10/ \
    --seed 42

# Full comparison — all targets (slow — requires WBIA startup)
python tests/benchmark/run_benchmark.py \
    --n-annots 10 --n-queries 3 \
    --targets wbia-core wbia-latest wbia-nightly wbia-develop

# Large-scale with reference
python tests/benchmark/run_benchmark.py \
    --n-annots 100 --n-queries 10 \
    --reference tests/benchmark/reference/wbia-latest-10/

# Species filter
python tests/benchmark/run_benchmark.py --species zebra_plains --reference tests/benchmark/reference/wbia-latest-10/
```

### Reference results

WBIA is deterministic across versions (ρ=1.0). Results only need to be recorded once:

```
tests/benchmark/reference/
└── wbia-latest-10/       # 10 annots, 3 queries, seed=42
    ├── manifest.json
    ├── query_000/
    │   ├── request.json
    │   └── response.json
    ├── query_001/
    └── query_002/
```

To create a new reference:
```bash
# Record WBIA results (one-time)
python tests/benchmark/run_benchmark.py \
    --n-annots 10 --n-queries 3 \
    --targets wbia-latest \
    --results-dir test-run-results-wbia-ref

# Save as reference
cp -r test-run-results-wbia-ref/target-wbia-latest/ \
    tests/benchmark/reference/wbia-latest-10/
```

All future runs use `--reference` for instant comparison — no WBIA container startup needed.

### Analysis

```bash
# Full report on a completed run
python tests/benchmark/analyze.py report test-run-results-20260606T101918/

# Replay fixtures through sidecar
python tests/benchmark/analyze.py fixtures --fixture-dir tests/replay/testdata/fixtures/

# Cross-check fixtures with benchmark
python tests/benchmark/analyze.py check test-run-results-20260606T101918/
```

### Comparison Metrics

| Metric | Description |
|---|---|
| **Top-1 identical** | All targets agree on #1 match |
| **All rankings match** | Complete ordering agreement across targets |
| **Max score delta** | Largest score difference between targets |
| **Spearman ρ** | Rank correlation coefficient (≥ 0.95 = strong agreement) |
| **Top-3 overlap** | Fraction of top-3 annotations shared between targets |
| **Score distribution** | μ, σ, range per target per query |

### Test data

The COCO dataset lives at `tests/test-dataset/`:

```
tests/test-dataset/
├── annotations/
│   ├── instances_train2020.json
│   ├── instances_val2020.json
│   └── instances_test2020.json
└── images/
    └── train2020/        # 4,948 wildlife images
```

### Running all benchmark tests

```bash
cd wbia-core
# Requires Docker + COCO dataset (test-dataset/ volume mount)
docker run --rm \
    -v $(pwd)/tests/test-dataset:/app/tests/test-dataset \
    --entrypoint bash wbia-core:latest -c \
    "pip install pytest -q && python -m pytest tests/benchmark/ -v --ignore=tests/benchmark/test_runner.py"
# 18 tests total
```

---

## Layer 3: Docker-Based Tests

All tests that require the compiled Docker image (pyhesaff, FLANN, OpenCV).

### Building the test image

```bash
cd wbia-core
docker build -t wbia-core:latest .
```

### Running tests inside the container

```bash
# Full test suite (excluding benchmark + replay)
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/ --ignore=tests/benchmark --ignore=tests/replay -v"

# Feature extraction test
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/test_features.py -v"

# Server smoke test
docker run -d --name test-server -p 5001:5000 wbia-core:latest
sleep 3
curl http://localhost:5001/api/health/
docker kill test-server
```

### Server entrypoint test

The server entrypoint boots gunicorn. Test with:

```bash
docker run --rm --entrypoint scripts/entrypoints/server-entrypoint.sh -d -p 5001:5000 wbia-core:latest
```

---

## Layer 4: Replay/Fixture Tests

Compare wbia-core against recorded WBIA identification results.

**Location:** `tests/replay/`

```
replay/
├── record_fixtures.py   # Generates synthetic images → WBIA → NPZ fixtures
├── test_replay.py       # Parametrized pytest: replay fixture through wbia-core
├── parity_test.py       # Standalone parity test (runs in Docker)
├── compare_knn.py       # FLANN output comparison
├── compare_knn_wbia.py  # FLANN vs WBIA comparison
├── compare_features.py  # Feature extraction comparison
├── patch_wbia_schema.py # WBIA schema patcher for SQLite mode
├── conftest.py          # Docker compose lifecycle (for live comparison only)
└── testdata/
    └── fixtures/        # Recorded NPZ fixtures (baked into Docker image)
```

### Fixture-based replay tests (self-contained)

NPZ fixtures are in the Docker image. No WBIA needed, no mounts needed:

```bash
# 84 fixture-based tests (no external services)
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/replay/ -v -k 'not TestLiveWbiaComparison'"
```

### Live WBIA comparison (1 test)

Needs WBIA running on localhost:5000 + Docker socket:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --network host \
  -e WBIA_URL=http://localhost:5000 --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/replay/ -v -k 'TestLiveWbiaComparison'"
```

---

## Test Quick Reference

```bash
cd wbia-core

# Everything you need for clean test infrastructure
docker build -t wbia-core:latest .                    # Build image once

# --- Run tests ---

# 1. Unit + integration (in Docker, guarantees pyhesaff)
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && pytest tests/ --ignore=tests/benchmark --ignore=tests/replay -v"

# 2. Sidecar endpoint tests
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && pytest tests/benchmark/sidecar/test_sidecar.py -v"

# 3. Benchmark pytest tests (needs dataset volume mount)
docker run --rm \
    -v $(pwd)/tests/test-dataset:/app/tests/test-dataset \
    --entrypoint bash wbia-core:latest -c \
    "pip install pytest -q && pytest tests/benchmark/ -v --ignore=tests/benchmark/test_runner.py"

# 4. Parity analysis (from HOST — uses docker CLI to start sidecar)
python3 tests/benchmark/run_benchmark.py \
    --n-annots 10 --n-queries 3 \
    --reference tests/benchmark/reference/wbia-latest-10/ \
    --seed 42

# 5. Analyze parity results
python3 tests/benchmark/analyze.py report test-results/<run-dir>/

# 6. Replay/fixture tests (self-contained, 84 tests)
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && pytest tests/replay/ -v -k 'not TestLiveWbiaComparison'"

# 7. Replay live WBIA comparison (1 test, needs WBIA on localhost:5000)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --network host \
  -e WBIA_URL=http://localhost:5000 --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && pytest tests/replay/ -v -k 'TestLiveWbiaComparison'"
```

## Test Commands Summary Table

| Command | What it tests | Runtime | Prerequisites |
|---|---|---|---|---|
| `make test-unit` | Unit + pipeline + scoring | < 2s | Docker |
| `make test-benchmark` | Benchmark pytest tests | ~20s | Docker + COCO dataset |
| `make test-parity` | COCO parity vs WBIA reference | ~10s | Host with Docker CLI |
| `make test-replay` | WBIA fixture replay (84 tests) | ~1 min | Docker (fixtures in image) |
| `make test-replay-live` | Live WBIA comparison (1 test) | ~30s | Docker socket + WBIA on :5000 |
| `python tests/benchmark/analyze.py report <dir>` | Result analysis | < 5s | Completed benchmark run |

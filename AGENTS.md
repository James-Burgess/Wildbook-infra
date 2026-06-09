# AGENTS.md

## Repository overview

Docker-orchestrated monorepo for the Wildbook wildlife conservation platform. Uses git submodules.

```
wildbook-infra/
├── docker-compose.yml    # Root orchestration: db, wbia, wildbook, opensearch, tests
├── wildbook-ia/          # WBIA Flask app (legacy, in maintenance)
├── wbia-core/            # NEW stateless HotSpotter pipeline (sidecar, Python package)
│   ├── src/wbia_core/    #   Package source (features, pipeline, knn, scoring, spatial)
│   ├── sidecar/api.py    #   Flask → single POST /api/v1/identify/
│   ├── wbia-utool/       #   vendored git submodule (pure Python utils)
│   ├── wbia-vtool/       #   vendored git submodule (vision tools, libsver.so)
│   ├── wbia-tpl-pyhesaff/#   vendored git submodule (hessian-affine SIFT, libhesaff.so)
│   └── Dockerfile        #   Self-contained Docker build
├── wildbook/             # Wildbook platform (Java/Tomcat, port 8080)
├── ml-service/           # ML service (Python, separate from wbia-core)
├── tests/                # BDD behave integration tests (Python)
├── wildbook-docs/        # Documentation
└── docs/                 # Infrastructure docs
```

## Two distinct Python projects

**`wildbook-ia`** — legacy WBIA. Controller-based architecture with dynamic method injection via `utool`. Plugin system, dual-database (SQLite/Postgres + DepCache). Not under active development.

**`wbia-core`** — stateless HotSpotter reimplementation extracted from `wildbook-ia`. Single-purpose: `POST /api/v1/identify/` returns scored matches. Uses vendored git submodules for `wbia-*` deps (source-compiled, not PyPI). **This is the canonical identification pipeline.**

## wbia-core build & test

### Build (Docker only)

wbia-core sells source-compiled submodules. The build order **must** be: `wbia-utool → wbia-vtool → wbia-tpl-pyhesaff → wbia-core`. The Dockerfile handles this with `SETUPTOOLS_SCM_PRETEND_VERSION` env vars and `pip install --no-deps` for each submodule, plus `python setup.py build_ext --inplace` for pyhesaff.

```bash
cd wbia-core
docker build -t wbia-core:latest .
```

### Run wbia-core tests

Use `make` from `wbia-core/` (see Makefile), or run directly:

```bash
# Fast unit tests (38 tests, <2s, self-contained):
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/ -q --ignore=tests/benchmark --ignore=tests/replay"

# Benchmark tests (needs test-dataset volume mount — it's in .dockerignore):
docker run --rm -v $(pwd)/tests/test-dataset:/app/tests/test-dataset \
  --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/benchmark/ -v --ignore=tests/benchmark/test_runner.py"

# Replay tests — fixture-based (84 tests, self-contained, NPZ fixtures baked into image):
docker run --rm --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/replay/ -v -k 'not TestLiveWbiaComparison'"

# Replay live comparison (1 test, needs WBIA running on localhost:5000 + Docker socket):
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --network host \
  -e WBIA_URL=http://localhost:5000 --entrypoint bash wbia-core:latest -c \
  "pip install pytest -q && python -m pytest tests/replay/ -v -k 'TestLiveWbiaComparison'"
```

### Parity analysis (from host, NOT inside Docker)

Runs wbia-core against COCO data and compares rankings to recorded WBIA reference:

```bash
cd wbia-core
python3 tests/benchmark/run_benchmark.py \
  --n-annots 10 --n-queries 3 \
  --reference tests/benchmark/reference/wbia-latest-10/ \
  --seed 42
```

**Must run from host** — the runner uses `docker` CLI to start the sidecar container. Results go to `test-results/test-run-results-*/`. Analyze with:
```bash
python3 tests/benchmark/analyze.py report test-results/<run-dir>/
```

### wbia-core API

```bash
docker run -d --name wbia-core -p 5000:5000 wbia-core:latest
curl http://localhost:5000/api/health/
curl -X POST http://localhost:5000/api/v1/identify/ \
  -H "Content-Type: application/json" -d @request.json
```

## wildbook-ia code quality

From `wildbook-ia/` (not wbia-core):

```bash
brunette --config=setup.cfg .     # Black fork, line-length=90, single quotes
isort --settings-path setup.cfg .  # black profile, line_length=90
flake8                              # config in setup.cfg [flake8] section
pre-commit run --all-files          # includes brunette + isort + flake8 + pyupgrade
```

**Note:** wbia-core does NOT use brunette/isort/flake8 — it has no code quality config.

## Integration tests (Behave BDD)

Tests live in `tests/` and run via Docker compose with the `tests` service:

```bash
docker-compose up -d db wbia wildbook opensearch   # prerequisites
docker-compose run --rm tests                       # all tests

# Or use the helper:
./tests/run-tests.sh all
./tests/run-tests.sh wbia          # WBIA-tagged tests only
./tests/run-tests.sh wildbook      # Wildbook-tagged tests only
./tests/run-tests.sh health        # health check tests
./tests/run-tests.sh feature features/health_checks.feature
```

## wildbook-ia legacy (for reference)

```bash
cd wildbook-ia
python -m wbia --db testdb1                # CLI mode
python -m wbia --web --port 5000           # web server
pytest                                      # run all tests
pytest -xvs wbia/tests/test_annots.py::test_func  # single test
```

Architecture: `IBEISController` (`wbia/control/IBEISControl.py`) is the central hub. Methods are injected at import time via `@register_ibs_method` decorator. Plugins auto-load from `wbia/control/`, `wbia/web/`, `wbia/other/`.

## Key gotchas

- **Submodule depth**: `wbia-core/wbia-utool`, `wbia-core/wbia-vtool`, `wbia-core/wbia-tpl-pyhesaff` are nested submodules. Clone with `--recursive` or `git submodule update --init --recursive`.
- **wbia-core has NO local install flow**. It runs exclusively in Docker. Source-compiled `.so` files (libhesaff, libsver) must match the container's OpenCV.
- **Replay tests are mostly self-contained**. 84/85 tests use baked-in NPZ fixtures — only `TestLiveWbiaComparison` (1 test) needs a running WBIA via Docker compose fixture.
- **`tests/test-dataset/` is dockerignored**. Benchmark tests that load COCO data need `-v $(pwd)/tests/test-dataset:/app/tests/test-dataset`.
- **Use the Makefile** in `wbia-core/` for shortcut commands: `make test`, `make test-benchmark`, `make test-replay`, `make shell`, `make server`.
- **The root `.env` file** must exist (copy from `.env.example`) for `docker-compose up`. Defaults are provided for all variables.
- **OpenSearch** on port 9200 uses `plugins.security.disabled=true` — no auth needed for dev.

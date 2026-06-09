# Wildbook Pipeline

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

Data pipeline for wildlife image analysis and identification, built with Kedro.

## Overview

This project processes wildlife images through a series of pipeline stages: raw data ingestion, preprocessing, feature extraction, and reporting.

Two deployment modes are available:
- **Development** — lightweight `docker-compose.yml` with Kedro, Viz, and docs
- **Production** — `docker-compose.prod.yml` with Apache Airflow (CeleryExecutor)

## Prerequisites

- Python 3.10+
- Docker & Docker Compose

## Quick Start

```bash
# Create venv and install dependencies
make install

# Run the pipeline
make run

# View the pipeline in Kedro Viz
make viz-up
# Then open http://localhost:4141
```

## Project Structure

```
pipeline/
├── Makefile                   # Common task shortcuts
├── Dockerfile                 # Kedro pipeline image
├── Dockerfile.viz             # Kedro Viz image
├── Dockerfile.airflow         # Airflow + Kedro image
├── docker-compose.yml         # Dev services (kedro, viz, docs)
├── docker-compose.prod.yml    # Production Airflow stack
├── dags/
│   └── wildbook_pipeline.py   # Airflow DAG definition
├── conf/
│   ├── base/
│   │   ├── catalog.yml        # Dataset definitions
│   │   └── parameters.yml     # Pipeline parameters
│   └── local/                 # Local overrides (gitignored)
├── data/
│   └── 01_raw/                # Raw input data
├── docs/                      # Static documentation (served by nginx)
├── notebooks/                 # Jupyter notebooks
├── src/
│   └── wildbook_pipeline/
│       └── pipelines/
│           └── example/       # Example pipeline definition
├── requirements.txt
└── pyproject.toml
```

## Makefile Targets

### Development

| Target            | Description                              |
|-------------------|------------------------------------------|
| `make install`    | Create venv and install dependencies     |
| `make run`        | Run the Kedro pipeline                   |
| `make test`       | Run tests                                |
| `make lint`       | Run flake8 and isort                     |
| `make clean`      | Remove venv, caches, and build artifacts |
| `make docker-up`  | Start dev containers (kedro + viz + docs)|
| `make docker-down`| Stop dev containers                      |
| `make viz-up`     | Start kedro-viz on port 4141             |
| `make viz-down`   | Stop kedro-viz                           |
| `make docs-up`    | Start docs nginx on port 8080            |
| `make docs-down`  | Stop docs nginx                          |

### Production (Airflow)

| Target            | Description                              |
|-------------------|------------------------------------------|
| `make prod-build` | Build the Airflow Docker image           |
| `make prod-init`  | Run DB migrations + create admin user    |
| `make prod-up`    | Start the full Airflow stack             |
| `make prod-down`  | Stop the Airflow stack                   |

## Services

### Development

| Service | Port  | Description                      |
|---------|-------|----------------------------------|
| kedro   | -     | Runs the data pipeline           |
| viz     | 4141  | Kedro pipeline visualization UI  |
| docs    | 8080  | Static docs served via nginx     |

### Production

| Service            | Port  | Description                      |
|--------------------|-------|----------------------------------|
| postgres           | -     | Airflow metadata database        |
| redis              | -     | Celery broker and result backend |
| airflow-webserver  | 8080  | Airflow UI                       |
| airflow-scheduler  | -     | DAG scheduling                   |
| airflow-triggerer  | -     | Deferrable operator execution    |
| airflow-worker     | -     | Celery task execution            |

## Production Deployment

```bash
# Build the Airflow image
make prod-build

# Initialize the database and create admin user
make prod-init

# Start the stack
make prod-up
```

Open `http://localhost:8080` and log in with `admin` / `admin`. The `wildbook_pipeline` DAG runs the example pipeline on a `@daily` schedule.

## Configuration

Environment-specific configuration lives in `conf/base/` with local overrides in `conf/local/`. Parameters are defined in `parameters.yml` and datasets in `catalog.yml`.

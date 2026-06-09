# Pipeline Test Plan

## Goal

A unified test harness that runs a fixed batch of images through three pipelines
(10.9, 10.10, new-ml) under two bbox regimes (COCO ground-truth, YOLO-detected)
and compares the ranked match results.

## Test matrix

| | COCO bboxes | YOLO bboxes |
|---|---|---|
| **10.9** (WBIA) | WBIA HotSpotter on ground-truth bboxes | N/A |
| **10.10** (ml + wbia-core) | skip detect → COCO bboxes → MiewID → identify | full flow: YOLO → MiewID → identify |
| **new-ml** (Kedro full DAG) | COCO bboxes through full DAG | YOLO through full DAG |

## Pipelines

| Pipeline | Status | Description |
|---|---|---|
| `identify_109` | done | WBIA REST API, COCO bboxes only |
| `identify` | done | 10.10: detect → extract → identify (YOLO bboxes) |
| `identify_1010_coco` | to build | 10.10 variant: COCO bboxes → embed → identify (no detection) |
| `new_ml` | to build | 8-node DAG from architecture doc, stubs for unimplemented nodes |

## new_ml pipeline nodes

| Node | Status | Detail |
|---|---|---|
| `minio_sensor` | stub | MinIO webhook not running |
| `detect` | done | calls ml-service `/predict/` |
| `classify` | stub | no classifier model in POC |
| `extract_miewid` | done | calls ml-service `/extract/` |
| `extract_hotspotter_sift` | stub | would use wbia-core pip package directly |
| `store_features` | stub | needs pgvector — writes to CSV for now |
| `identify` | done | calls wbia-core `/api/v1/identify/` |
| `notify` | stub | needs PostgreSQL NOTIFY |

## File structure

```
pipeline/tests/
├── conftest.py              # batch loader, service URLs, shared fixture
├── reference_batch.json     # fixed seed=42, 10 images, 3 queries (deterministic)
├── test_compare_coco.py     # compare 10.9 vs 10.10 vs new_ml on COCO bboxes
├── test_compare_yolo.py     # compare 10.10 vs new_ml on YOLO bboxes
└── test_yolo_vs_coco.py     # measure detection drift impact on match rankings

pipeline/src/wildbook_pipeline/pipelines/
├── identify_1010_coco/      # new: 10.10 with COCO bboxes (no YOLO detect)
└── new_ml/                  # new: full target architecture pipeline with stubs
```

## Metrics

| Metric | What it measures |
|---|---|
| Top-1 agreement | same top-ranked match across pipelines |
| Top-3 overlap | fraction of top-3 in both pipelines |
| Spearman ρ | rank correlation of scores |
| YOLO vs COCO delta | detection quality impact on identification rankings |

## Output format

```json
{
  "batch": {"n_images": 10, "n_queries": 3, "seed": 42},
  "pipelines": {
    "10.9": {"status": "completed", "queries": [...]},
    "10.10_coco": {"status": "completed", "queries": [...]},
    "10.10_yolo": {"status": "completed", "queries": [...]},
    "new_ml_coco": {"status": "partial", "completed_nodes": [...], "stubbed_nodes": [...]},
    "new_ml_yolo": {"status": "partial", "completed_nodes": [...], "stubbed_nodes": [...]}
  },
  "comparison": {
    "coco_109_vs_1010": {"top1": xx, "spearman": xx},
    "coco_109_vs_new_ml": {"top1": xx, "spearman": xx},
    "yolo_1010_vs_new_ml": {"top1": xx, "spearman": xx},
    "yolo_vs_coco_delta": {"top1_drift": xx, "spearman_drift": xx}
  }
}
```

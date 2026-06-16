"""Pipeline comparison tests — runs 10.9, 10.10, and new_ml on the fixed
reference batch under COCO and YOLO bbox regimes, then compares results."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from wildbook_pipeline.pipelines.tests.identify.nodes import (
    detect,
    extract_miewid,
    identify_hotspotter,
)
from wildbook_pipeline.pipelines.tests.identify_109.nodes import identify_wbia
from wildbook_pipeline.pipelines.tests.identify_1010_coco.nodes import (
    prepare_coco_bboxes,
)
from wildbook_pipeline.pipelines.new_ml.nodes import (
    classify,
    extract_hotspotter_sift,
    store_features,
)

from ._metrics import (
    compare_queries,
    norm_1010_results,
    norm_109_results,
    save_comparison,
)
from .conftest import requires_service

_RESULTS_DIR = Path("/app/data/08_reporting")


@pytest.fixture(scope="module")
def results_dir():
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return _RESULTS_DIR


# ---------------------------------------------------------------------------
# 10.9 COCO (WBIA HotSpotter on ground-truth bboxes)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results_109_coco(reference_batch, wbia_url, results_dir):
    requires_service(wbia_url)
    images = copy.deepcopy(reference_batch["annotations"])
    identified = identify_wbia(images, wbia_url)
    norm = norm_109_results(identified)
    save_comparison(results_dir / "results_109_coco.json", norm)
    return norm


def test_109_coco_completed(results_109_coco):
    assert len(results_109_coco) > 0, "No query results from 10.9"


def test_109_coco_has_ranks(results_109_coco):
    for r in results_109_coco:
        assert len(r["ranks"]) > 0, f"No ranks for query {r['query_annot_id']}"


# ---------------------------------------------------------------------------
# 10.10 COCO (ml-service MiewID + wbia-core HotSpotter, COCO bboxes)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results_1010_coco(
    reference_batch,
    ml_service_url,
    wbia_core_url,
    extract_model_id,
    identify_config,
    results_dir,
):
    requires_service(ml_service_url)
    requires_service(wbia_core_url)
    images = copy.deepcopy(reference_batch["annotations"])
    images = prepare_coco_bboxes(images)
    images = extract_miewid(images, ml_service_url, extract_model_id)
    images = identify_hotspotter(
        images, images, wbia_core_url, identify_config, max_db_entries=19
    )
    norm = norm_1010_results(images)
    save_comparison(results_dir / "results_1010_coco.json", norm)
    return norm


def test_1010_coco_completed(results_1010_coco):
    assert len(results_1010_coco) > 0, "No query results from 10.10 COCO"


def test_1010_coco_has_ranks(results_1010_coco):
    for r in results_1010_coco:
        assert len(r["ranks"]) > 0, f"No ranks for query {r['query_annot_id']}"


# ---------------------------------------------------------------------------
# 10.10 YOLO (ml-service YOLO detect + MiewID + wbia-core HotSpotter)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results_1010_yolo(
    reference_batch,
    ml_service_url,
    wbia_core_url,
    predict_model_id,
    extract_model_id,
    identify_config,
    predict_params,
    results_dir,
):
    requires_service(ml_service_url)
    requires_service(wbia_core_url)
    images = copy.deepcopy(reference_batch["annotations"])
    images = detect(images, ml_service_url, predict_model_id, predict_params)
    images = extract_miewid(images, ml_service_url, extract_model_id)
    queries = [img for img in images if img.get("is_query")]
    images = identify_hotspotter(
        queries, images, wbia_core_url, identify_config, max_db_entries=19
    )
    norm = norm_1010_results(images)
    save_comparison(results_dir / "results_1010_yolo.json", norm)
    return norm


def test_1010_yolo_completed(results_1010_yolo):
    assert len(results_1010_yolo) > 0, "No query results from 10.10 YOLO"


def test_1010_yolo_has_ranks(results_1010_yolo):
    for r in results_1010_yolo:
        assert len(r["ranks"]) > 0, f"No ranks for query {r['query_annot_id']}"


# ---------------------------------------------------------------------------
# new_ml YOLO (full DAG: detect → classify → miewid → sift → store → identify)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results_newml_yolo(
    reference_batch,
    ml_service_url,
    wbia_core_url,
    predict_model_id,
    extract_model_id,
    identify_config,
    predict_params,
    results_dir,
):
    requires_service(ml_service_url)
    requires_service(wbia_core_url)
    images = copy.deepcopy(reference_batch["annotations"])
    images = detect(images, ml_service_url, predict_model_id, predict_params)
    images = classify(images, ["plains_zebra", "grevys_zebra"])
    images = extract_miewid(images, ml_service_url, extract_model_id)
    images = extract_hotspotter_sift(images)
    images = store_features(images, str(results_dir / "features_newml.csv"))
    queries = [img for img in images if img.get("is_query")]
    images = identify_hotspotter(
        queries, images, wbia_core_url, identify_config, max_db_entries=19
    )
    norm = norm_1010_results(images)
    save_comparison(results_dir / "results_newml_yolo.json", norm)
    return norm


def test_newml_yolo_completed(results_newml_yolo):
    assert len(results_newml_yolo) > 0, "No query results from new_ml YOLO"


def test_newml_yolo_has_ranks(results_newml_yolo):
    for r in results_newml_yolo:
        assert len(r["ranks"]) > 0, f"No ranks for query {r['query_annot_id']}"


# ---------------------------------------------------------------------------
# new_ml COCO (full DAG with COCO bboxes injected after detect)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results_newml_coco(
    reference_batch,
    ml_service_url,
    wbia_core_url,
    extract_model_id,
    identify_config,
    results_dir,
):
    requires_service(ml_service_url)
    requires_service(wbia_core_url)
    images = copy.deepcopy(reference_batch["annotations"])
    images = prepare_coco_bboxes(images)
    images = classify(images, ["plains_zebra", "grevys_zebra"])
    images = extract_miewid(images, ml_service_url, extract_model_id)
    images = extract_hotspotter_sift(images)
    images = store_features(images, str(results_dir / "features_newml_coco.csv"))
    images = identify_hotspotter(
        images, images, wbia_core_url, identify_config, max_db_entries=19
    )
    norm = norm_1010_results(images)
    save_comparison(results_dir / "results_newml_coco.json", norm)
    return norm


def test_newml_coco_completed(results_newml_coco):
    assert len(results_newml_coco) > 0, "No query results from new_ml COCO"


# ---------------------------------------------------------------------------
# COMPARISONS
# ---------------------------------------------------------------------------


def test_compare_109_vs_1010_coco(results_109_coco, results_1010_coco, results_dir):
    comp = compare_queries(results_109_coco, results_1010_coco, "109", "1010")
    save_comparison(results_dir / "compare_109_vs_1010_coco.json", comp)
    assert comp["top1_agreement"] is not None
    assert isinstance(comp["spearman_mean"], float)


def test_compare_1010_vs_newml_coco(results_1010_coco, results_newml_coco, results_dir):
    comp = compare_queries(results_1010_coco, results_newml_coco, "1010c", "newml")
    save_comparison(results_dir / "compare_1010_vs_newml_coco.json", comp)
    assert comp["top1_agreement"] is not None
    assert isinstance(comp["spearman_mean"], float)


def test_compare_109_vs_newml_coco(results_109_coco, results_newml_coco, results_dir):
    comp = compare_queries(results_109_coco, results_newml_coco, "109", "newml")
    save_comparison(results_dir / "compare_109_vs_newml_coco.json", comp)
    assert comp["top1_agreement"] is not None
    assert isinstance(comp["spearman_mean"], float)


def test_compare_1010_vs_newml_yolo(results_1010_yolo, results_newml_yolo, results_dir):
    comp = compare_queries(results_1010_yolo, results_newml_yolo, "1010y", "newml")
    save_comparison(results_dir / "compare_1010_vs_newml_yolo.json", comp)
    assert comp["top1_agreement"] is not None
    assert isinstance(comp["spearman_mean"], float)


def test_compare_yolo_vs_coco_drift(results_1010_yolo, results_1010_coco, results_dir):
    comp = compare_queries(results_1010_yolo, results_1010_coco, "yolo", "coco")
    save_comparison(results_dir / "compare_yolo_vs_coco.json", comp)
    assert comp["top1_agreement"] is not None
    assert isinstance(comp["spearman_mean"], float)

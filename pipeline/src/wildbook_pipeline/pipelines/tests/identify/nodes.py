from __future__ import annotations

import base64
import json
import random as _random
import time
from pathlib import Path
from typing import Any

import requests

from ...new_ml._core import (
    b64 as _b64,
    load_image_bytes as _load_image_bytes,
    resolve_coco_image as _resolve_coco_image,
)


def load_dataset(
    coco_json_path: str,
    coco_images_path: str,
    n_images: int = 10,
    n_query: int = 3,
    seed: int = 42,
) -> list[dict]:
    with open(coco_json_path) as f:
        coco = json.load(f)

    images_by_id = {img["id"]: img for img in coco["images"]}
    annotations = coco.get("annotations", [])

    rng = _random.Random(seed)
    rng.shuffle(annotations)
    selected = [
        _normalize_coco_annot(a, images_by_id, coco_images_path)
        for a in annotations[:n_images]
    ]

    query_indices = set(rng.sample(range(len(selected)), min(n_query, len(selected))))

    for i, img in enumerate(selected):
        img["is_query"] = i in query_indices

    return selected


def _normalize_coco_annot(
    ann: dict,
    images_by_id: dict,
    coco_images_path: str,
) -> dict:
    img_info = images_by_id.get(ann["image_id"], {})
    file_name = img_info.get("file_name", "")
    return {
        "uri": _resolve_coco_image(coco_images_path, file_name),
        "annot_id": ann["id"],
        "file_name": file_name,
        "image_id": ann["image_id"],
        "bbox": ann["bbox"],
        "category_id": ann.get("category_id", -1),
        "individual_ids": ann.get("individual_ids", []),
    }


def detect(
    images: list[dict],
    ml_service_url: str,
    predict_model_id: str,
    predict_params: dict | None = None,
) -> list[dict]:
    url = f"{ml_service_url}/predict/"
    results = []
    for img in images:
        r = requests.post(
            url,
            json={
                "model_id": predict_model_id,
                "image_uri": img["uri"],
                "model_params": predict_params or {},
            },
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        img["detections"] = data
        results.append(img)
    return results


def extract_miewid(
    images_with_detections: list[dict],
    ml_service_url: str,
    extract_model_id: str,
    score_threshold: float = 0.25,
) -> list[dict]:
    url = f"{ml_service_url}/extract/"
    results = []
    for img in images_with_detections:
        dets = img.get("detections", {})
        bboxes = dets.get("bboxes", [])
        scores = dets.get("scores", [])
        thetas = dets.get("thetas", [0.0] * len(bboxes))
        chips = []
        for i, bbox in enumerate(bboxes):
            if scores[i] < score_threshold:
                continue
            r = requests.post(
                url,
                json={
                    "extract_model_id": extract_model_id,
                    "image_uri": img["uri"],
                    "bbox": bbox,
                    "theta": thetas[i] if i < len(thetas) else 0.0,
                },
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            chips.append(
                {
                    "bbox": bbox,
                    "theta": thetas[i] if i < len(thetas) else 0.0,
                    "score": scores[i],
                    "embedding": data.get("embedding", []),
                    "embedding_model_id": data.get("embedding_model_id", ""),
                    "embedding_model_version": data.get("embedding_model_version", ""),
                }
            )
        img["chips"] = chips
        results.append(img)
    return results


def identify_hotspotter(
    images_with_embeddings: list[dict],
    database: list[dict],
    wbia_core_url: str,
    identify_config: dict | None = None,
    max_db_entries: int = 30,
) -> list[dict]:
    url = f"{wbia_core_url}/api/v1/identify/"
    db_slice = database[:max_db_entries]
    db_entries = []
    for db_img in db_slice:
        img_bytes = _load_image_bytes(db_img["uri"])
        db_entries.append(
            {
                "aid": f"coco-annot-{db_img['annot_id']}",
                "image_b64": _b64(img_bytes),
                "bbox": db_img["bbox"],
            }
        )
    results = []
    for img in images_with_embeddings:
        img_bytes = _load_image_bytes(img["uri"])
        for chip in img.get("chips", []):
            if not db_entries:
                chip["hotspotter_scores"] = []
                chip["hotspotter_timing_ms"] = 0
                continue
            r = requests.post(
                url,
                json={
                    "query_image_b64": _b64(img_bytes),
                    "query_bbox": chip["bbox"],
                    "database": db_entries,
                    "config": identify_config or {},
                },
                timeout=600,
            )
            r.raise_for_status()
            data = r.json()
            chip["hotspotter_scores"] = (
                data.get("response", {}).get("annot_scores", [])
                if data.get("status") == "completed"
                else []
            )
            chip["hotspotter_timing_ms"] = (
                data.get("response", {}).get("timing_ms", 0)
                if data.get("status") == "completed"
                else 0
            )
        results.append(img)
    return results


def store_results(identified: list[dict], output_path: str) -> list[dict]:
    summary = []
    for img in identified:
        for chip in img.get("chips", []):
            summary.append(
                {
                    "uri": img["uri"],
                    "bbox": chip["bbox"],
                    "theta": chip.get("theta", 0.0),
                    "score": chip.get("score", 0.0),
                    "classification": chip.get("classification"),
                    "embedding": chip.get("embedding", [])[:16],
                    "hotspotter_top": (
                        chip.get("hotspotter_scores", [{}])[0]
                        if chip.get("hotspotter_scores")
                        else None
                    ),
                }
            )
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary

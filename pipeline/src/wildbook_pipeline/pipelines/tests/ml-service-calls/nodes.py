from __future__ import annotations

import json
from pathlib import Path

import requests

from ...new_ml._core import (
    b64 as _b64,
    load_image_bytes as _load_image_bytes,
    resolve_coco_image as _resolve_coco_image,
)


def minio_sensor(coco_json_path: str) -> str:
    return coco_json_path


def load_from_url(
    raw_images: str,
    coco_images_path: str,
    coco_json_path: str,
) -> list[dict]:
    with open(coco_json_path) as f:
        coco = json.load(f)

    images_by_id = {img["id"]: img for img in coco["images"]}
    annotations = coco.get("annotations", [])

    return [
        {
            "uri": _resolve_coco_image(
                coco_images_path, images_by_id[a["image_id"]]["file_name"]
            ),
            "annot_id": a["id"],
            "file_name": images_by_id[a["image_id"]]["file_name"],
            "image_id": a["image_id"],
            "bbox": a["bbox"],
            "category_id": a.get("category_id", -1),
            "individual_ids": a.get("individual_ids", []),
        }
        for a in annotations[:10]
    ]


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


def classify(images: list[dict]) -> list[dict]:
    for img in images:
        img["classification"] = "zebra_plains"
    return images


def extract_miewid(
    images: list[dict],
    ml_service_url: str,
    extract_model_id: str,
    score_threshold: float = 0.25,
) -> list[dict]:
    url = f"{ml_service_url}/extract/"
    results = []
    for img in images:
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


def extract_hotspotter_sift(images: list[dict]) -> list[dict]:
    return images


def store_features(images: list[dict], feature_store_csv: str) -> list[dict]:
    Path(feature_store_csv).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for img in images:
        for chip in img.get("chips", []):
            rows.append(
                {
                    "annot_id": img["annot_id"],
                    "bbox": chip["bbox"],
                    "species": img.get("classification", ""),
                    "embedding_dim": len(chip.get("embedding", [])),
                }
            )
    import csv

    if rows:
        with open(feature_store_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    return images


def identify(
    images: list[dict],
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
    for img in images:
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
                    "classification": chip.get("classification", ""),
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


def notify(identified: list[dict]) -> list[dict]:
    return identified

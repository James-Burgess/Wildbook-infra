from __future__ import annotations

import json

from ._core import logger, resolve_coco_image


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
            "uri": resolve_coco_image(
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

from __future__ import annotations


def prepare_coco_bboxes(images: list[dict]) -> list[dict]:
    for img in images:
        img["detections"] = {
            "bboxes": [img["bbox"]],
            "scores": [1.0],
            "thetas": [0.0],
        }
    return images

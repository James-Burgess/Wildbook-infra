from __future__ import annotations

import time

import cv2
import numpy as np

from ._core import (
    load_onnx_model,
    extract_chip,
    get_image_arrays,
    apply_mask,
    _IMAGENET_MEAN,
    _IMAGENET_STD,
    logger,
)


def extract_miewid(
    images: list[dict],
    onnx_model_dir: str,
    onnx_miewid_model: str,
    onnx_miewid_repo: str,
    miewid_imgsz: int = 440,
    score_threshold: float = 0.25,
) -> list[dict]:
    net = load_onnx_model(onnx_model_dir, onnx_miewid_repo, onnx_miewid_model)
    mean_255 = _IMAGENET_MEAN * 255.0

    results = []
    for img in images:
        bgr, rgb = get_image_arrays(img)
        if bgr is None:
            logger.warning("Could not read image: %s", img["uri"])
            img["chips"] = []
            results.append(img)
            continue

        dets = img.get("detections", {})
        bboxes = dets.get("bboxes", [])
        scores = dets.get("scores", [])
        thetas = dets.get("thetas", [0.0] * len(bboxes))
        classifications = dets.get("classifications", [])
        chips = []

        for i, bbox in enumerate(bboxes):
            if scores[i] < score_threshold:
                continue

            theta = thetas[i] if i < len(thetas) else 0.0
            chip_rgb = extract_chip(rgb, bbox, theta)
            chip_rgb = apply_mask(chip_rgb)

            chip_resized = cv2.resize(
                chip_rgb.astype(np.float32),
                (miewid_imgsz, miewid_imgsz),
                interpolation=cv2.INTER_LINEAR,
            )
            chip_norm = (chip_resized - mean_255) / (_IMAGENET_STD * 255.0)

            blob = np.transpose(chip_norm, (2, 0, 1)).astype(np.float32)
            blob = np.expand_dims(blob, axis=0)

            net.setInput(blob)
            t0 = time.monotonic()
            embedding = net.forward()
            elapsed = time.monotonic() - t0

            cls_info = classifications[i] if i < len(classifications) else {}

            chips.append(
                {
                    "bbox": bbox,
                    "theta": theta,
                    "score": scores[i],
                    "classification": cls_info.get("species", ""),
                    "classification_score": cls_info.get("score", 0.0),
                    "embedding": embedding.flatten().tolist(),
                    "embedding_model_id": onnx_miewid_model,
                    "embedding_model_version": "onnx",
                    "extract_timing_ms": round(elapsed * 1000, 1),
                }
            )

        img["chips"] = chips
        results.append(img)

    return results

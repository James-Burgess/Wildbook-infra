from __future__ import annotations

import time

import cv2
import numpy as np

from ._core import (
    load_onnx_model,
    parse_yolo_output,
    read_bgr,
    downscale_bgr,
    logger,
)


def detect(
    images: list[dict],
    onnx_model_dir: str,
    onnx_yolo_model: str,
    onnx_yolo_repo: str,
    onnx_yolo_subdir: str = "",
    yolo_imgsz: int = 640,
    yolo_conf_threshold: float = 0.25,
    yolo_nms_threshold: float = 0.45,
    image_max_dim: int = 1024,
) -> list[dict]:
    net = load_onnx_model(
        onnx_model_dir, onnx_yolo_repo, onnx_yolo_model, onnx_yolo_subdir or None
    )
    results = []

    for img in images:
        bgr = read_bgr(img["uri"])
        if bgr is None:
            logger.warning("Could not read image: %s", img["uri"])
            img["detections"] = {
                "bboxes": [],
                "scores": [],
                "thetas": [],
                "class_names": [],
            }
            results.append(img)
            continue

        orig_h, orig_w = bgr.shape[:2]
        bgr_scaled = downscale_bgr(bgr, image_max_dim)
        img["bgr"] = bgr_scaled
        img["orig_h"] = orig_h
        img["orig_w"] = orig_w

        scaled_h, scaled_w = bgr_scaled.shape[:2]
        blob = cv2.dnn.blobFromImage(
            bgr_scaled, 1 / 255.0, (yolo_imgsz, yolo_imgsz), swapRB=True, crop=False
        )
        net.setInput(blob)
        t0 = time.monotonic()
        outputs = net.forward()
        elapsed = time.monotonic() - t0

        bboxes, scores, class_ids = parse_yolo_output(
            outputs,
            scaled_w,
            scaled_h,
            yolo_imgsz,
            yolo_conf_threshold,
            yolo_nms_threshold,
        )
        img["detections"] = {
            "bboxes": bboxes,
            "scores": scores,
            "thetas": [0.0] * len(bboxes),
            "class_names": [str(c) for c in class_ids],
        }
        img["detect_timing_ms"] = round(elapsed * 1000, 1)
        results.append(img)

    return results

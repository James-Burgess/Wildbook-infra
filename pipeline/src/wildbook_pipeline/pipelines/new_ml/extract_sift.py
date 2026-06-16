from __future__ import annotations

import cv2
import numpy as np

from ._core import extract_chip, get_image_arrays


def extract_hotspotter_sift(images: list[dict]) -> list[dict]:
    sift = cv2.SIFT_create()
    for img in images:
        bgr, rgb = get_image_arrays(img)
        if bgr is None:
            continue

        for chip in img.get("chips", []):
            bbox = chip["bbox"]
            theta = chip.get("theta", 0.0)
            chip_rgb = extract_chip(rgb, bbox, theta)
            gray = cv2.cvtColor(chip_rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)

            kp, des = sift.detectAndCompute(gray, None)

            chip["sift_keypoints"] = len(kp)
            chip["sift_descriptors"] = (
                des.astype(np.float16).tolist() if des is not None else []
            )
            chip["sift_descriptor_dim"] = des.shape[1] if des is not None else 0

    return images

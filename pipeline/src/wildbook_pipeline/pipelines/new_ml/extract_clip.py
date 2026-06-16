from __future__ import annotations

import torch
import numpy as np
from PIL import Image

from ._core import extract_chip, get_image_arrays, get_clip_model, apply_mask

_CLIP = None


def _get_clip():
    global _CLIP
    if _CLIP is None:
        _CLIP = get_clip_model()
    return _CLIP


def extract_clip(images: list[dict], clip_model_name: str = "ViT-B-32") -> list[dict]:
    model, preprocess, _ = _get_clip()
    device = next(model.parameters()).device

    for img in images:
        bgr, rgb = get_image_arrays(img)
        if bgr is None:
            img["detections"]["clip_embeddings"] = []
            continue

        dets = img.get("detections", {})
        bboxes = dets.get("bboxes", [])
        thetas = dets.get("thetas", [0.0] * len(bboxes))

        clip_embs = []
        for i, bbox in enumerate(bboxes):
            theta = thetas[i] if i < len(thetas) else 0.0
            chip_rgb = extract_chip(rgb, bbox, theta)
            chip_rgb = apply_mask(chip_rgb)

            pil_img = Image.fromarray(chip_rgb.astype(np.uint8))
            inp = preprocess(pil_img).unsqueeze(0).to(device)

            with torch.inference_mode():
                clip_vec = model.encode_image(inp)
                clip_vec = clip_vec / clip_vec.norm(dim=-1, keepdim=True)

            clip_embs.append(
                {
                    "embedding": clip_vec.cpu().numpy().flatten().tolist(),
                    "dim": clip_vec.shape[-1],
                }
            )

        img["detections"]["clip_embeddings"] = clip_embs

    return images

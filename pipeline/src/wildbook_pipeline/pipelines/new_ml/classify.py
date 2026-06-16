from __future__ import annotations

import numpy as np

from ._core import get_clip_model, logger

_CLIP_MODEL = None


def _get_clip():
    global _CLIP_MODEL
    if _CLIP_MODEL is None:
        _CLIP_MODEL = get_clip_model()
    return _CLIP_MODEL


def classify(images: list[dict], species_labels: list[str]) -> list[dict]:
    import torch
    import faiss

    model, _, tokenizer = _get_clip()
    device = next(model.parameters()).device

    prompts = [f"a photo of a {s.replace('_', ' ')}" for s in species_labels]
    text_tokens = tokenizer(prompts).to(device)

    with torch.inference_mode():
        text_features = model.encode_text(text_tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    text_np = text_features.cpu().numpy().astype(np.float32)
    dim = text_np.shape[1]

    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(text_np)
    index.add(text_np)

    for img in images:
        dets = img.get("detections", {})
        clip_embs = dets.get("clip_embeddings", [])
        classifications = []
        for emb in clip_embs:
            vec = emb.get("embedding", [])
            if not vec:
                classifications.append({"species": "unknown", "score": 0.0})
                continue

            query = np.array([vec], dtype=np.float32)
            faiss.normalize_L2(query)
            distances, indices = index.search(query, 1)

            best_idx = indices[0][0]
            classifications.append(
                {
                    "species": species_labels[best_idx],
                    "score": float(distances[0][0]),
                }
            )

        img["detections"]["classifications"] = classifications
        logger.debug(
            "%s: %s",
            img.get("file_name", ""),
            [c["species"] for c in classifications],
        )

    return images


def notify(identified: list[dict]) -> list[dict]:
    return identified

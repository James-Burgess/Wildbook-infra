from __future__ import annotations

from pathlib import Path

import numpy as np

from ._core import logger


def _ensure_faiss():
    try:
        import faiss

        return faiss
    except ImportError:
        logger.warning("faiss not installed, skipping index build")
        return None


def build_faiss_clip(
    images: list[dict],
    faiss_index_dir: str = "/app/data/09_index",
) -> list[dict]:
    faiss = _ensure_faiss()
    if faiss is None:
        return images

    vecs = []
    for img in images:
        for emb in img.get("detections", {}).get("clip_embeddings", []):
            if emb.get("embedding"):
                vecs.append(emb["embedding"])

    if vecs:
        dim = len(vecs[0])
        arr = np.array(vecs, dtype=np.float32)
        faiss.normalize_L2(arr)
        index = faiss.IndexFlatIP(dim)
        index.add(arr)
        path = str(Path(faiss_index_dir) / "clip.index")
        Path(faiss_index_dir).mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, path)
        logger.info("CLIP FAISS: %d vectors, dim=%d → %s", len(vecs), dim, path)

    return images


def build_faiss_miewid(
    images: list[dict],
    faiss_index_dir: str = "/app/data/09_index",
) -> list[dict]:
    faiss = _ensure_faiss()
    if faiss is None:
        return images

    vecs = []
    for img in images:
        for chip in img.get("chips", []):
            emb = chip.get("embedding", [])
            if emb:
                vecs.append(emb)

    if vecs:
        dim = len(vecs[0])
        arr = np.array(vecs, dtype=np.float32)
        faiss.normalize_L2(arr)
        index = faiss.IndexFlatIP(dim)
        index.add(arr)
        path = str(Path(faiss_index_dir) / "miewid.index")
        Path(faiss_index_dir).mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, path)
        logger.info("MiewID FAISS: %d vectors, dim=%d → %s", len(vecs), dim, path)

    return images

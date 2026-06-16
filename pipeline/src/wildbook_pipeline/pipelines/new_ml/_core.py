from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_MODEL_CACHE: dict[str, Any] = {}

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def b64(img: bytes) -> str:
    return base64.b64encode(img).decode("utf-8")


def load_image_bytes(image_uri: str) -> bytes:
    if image_uri.startswith(("http://", "https://")):
        import requests

        resp = requests.get(image_uri, timeout=120)
        resp.raise_for_status()
        return resp.content
    return Path(image_uri).read_bytes()


def resolve_coco_image(coco_images_path: str, file_name: str) -> str:
    base = Path(coco_images_path)
    for subdir in ("train2020", "val2020", "test2020"):
        candidate = base / subdir / file_name
        if candidate.exists():
            return str(candidate)
    return str(base / file_name)


def hf_download(
    repo_id: str,
    filename: str,
    cache_dir: str = "/app/models",
    subfolder: str | None = None,
) -> str:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise ImportError(
            "huggingface_hub is required for model download. "
            "Install it with: pip install huggingface_hub"
        )

    kwargs = dict(repo_id=repo_id, filename=filename, cache_dir=cache_dir)
    if subfolder:
        kwargs["subfolder"] = subfolder
    local = hf_hub_download(**kwargs)
    logger.info("Downloaded %s/%s/%s → %s", repo_id, subfolder or "", filename, local)
    return local


def load_onnx_model(
    model_path: str,
    repo_id: str,
    filename: str,
    subfolder: str | None = None,
) -> cv2.dnn.Net:
    cache_key = (repo_id, filename, subfolder or "")
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    local = Path(model_path) / filename
    if not local.exists():
        logger.info("Model not found at %s, downloading...", local)
        downloaded = hf_download(repo_id, filename, str(Path(model_path)), subfolder)
        local = Path(downloaded)

    net = cv2.dnn.readNetFromONNX(str(local))
    _MODEL_CACHE[cache_key] = net
    logger.info("Loaded ONNX model: %s (%s)", filename, local)
    return net


def read_bgr(image_path: str) -> np.ndarray | None:
    if image_path.startswith(("http://", "https://")):
        import requests

        resp = requests.get(image_path, timeout=120)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.imread(image_path, cv2.IMREAD_COLOR)


def read_bgr_to_rgb(image_path: str) -> tuple[np.ndarray | None, np.ndarray | None]:
    bgr = read_bgr(image_path)
    if bgr is None:
        return None, None
    return bgr, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def get_image_arrays(img: dict) -> tuple[np.ndarray | None, np.ndarray | None]:
    if "bgr" in img:
        bgr = img["bgr"]
        return bgr, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    bgr = read_bgr(img["uri"])
    if bgr is None:
        return None, None
    return bgr, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def downscale_bgr(bgr: np.ndarray, max_dim: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    if max(w, h) <= max_dim:
        return bgr
    scale = max_dim / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)


def extract_chip(
    rgb: np.ndarray,
    bbox: list[float],
    theta: float,
) -> np.ndarray:
    x, y, w, h = bbox
    cx = x + w / 2.0
    cy = y + h / 2.0

    if abs(theta) < 1e-6:
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(rgb.shape[1], int(x + w))
        y1 = min(rgb.shape[0], int(y + h))
        return rgb[y0:y1, x0:x1]

    src_pts = np.array(
        [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
        dtype=np.float32,
    )

    cos_t = np.cos(-theta)
    sin_t = np.sin(-theta)

    pts_centered = src_pts - np.array([[cx, cy]], dtype=np.float32)
    rot_x = pts_centered[:, 0] * cos_t - pts_centered[:, 1] * sin_t
    rot_y = pts_centered[:, 0] * sin_t + pts_centered[:, 1] * cos_t

    min_x = rot_x.min()
    max_x = rot_x.max()
    min_y = rot_y.min()
    max_y = rot_y.max()

    dst_w = int(np.ceil(max_x - min_x))
    dst_h = int(np.ceil(max_y - min_y))

    M = cv2.getRotationMatrix2D((cx, cy), np.degrees(-theta), 1.0)
    M[0, 2] -= min_x
    M[1, 2] -= min_y

    return cv2.warpAffine(
        rgb,
        M,
        (dst_w, dst_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )


def parse_yolo_output(
    outputs,
    orig_w: int,
    orig_h: int,
    imgsz: int,
    conf_threshold: float,
    nms_threshold: float,
) -> tuple[list[list[float]], list[float], list[int]]:
    if isinstance(outputs, tuple):
        outputs = outputs[0]
    if isinstance(outputs, list):
        outputs = np.array(outputs)
    if outputs.ndim == 4:
        outputs = outputs[0]
    if outputs.ndim != 3:
        return [], [], []

    batch, dim1, dim2 = outputs.shape

    if dim2 == 4:
        boxes = outputs[0]
        cx, cy, bw, bh = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        x1 = ((cx - bw / 2) * orig_w).clip(0, orig_w)
        y1 = ((cy - bh / 2) * orig_h).clip(0, orig_h)
        w = (bw * orig_w).clip(1, orig_w - x1)
        h = (bh * orig_h).clip(1, orig_h - y1)

        min_dim = min(orig_w, orig_h)
        area = w * h
        keep = area > (min_dim * 0.02) ** 2
        if not keep.any():
            return [], [], []

        boxes_xywh = [
            [float(x), float(y), float(b), float(hh)]
            for x, y, b, hh in zip(x1[keep], y1[keep], w[keep], h[keep])
        ]
        indices = cv2.dnn.NMSBoxes(
            boxes_xywh, [1.0] * len(boxes_xywh), 0.0, nms_threshold
        )
        if not len(indices):
            return boxes_xywh, [1.0] * len(boxes_xywh), [0] * len(boxes_xywh)

        if isinstance(indices[0], (list, tuple)):
            kept = [int(idx[0]) for idx in indices]
        else:
            kept = [int(idx) for idx in indices.flatten()]
        return [boxes_xywh[i] for i in kept], [1.0] * len(kept), [0] * len(kept)

    num_classes = dim1 - 4
    outputs = outputs[0]
    bbox_raw = outputs[:4]
    class_scores = outputs[4:] if num_classes > 0 else None
    max_scores = class_scores.max(axis=0) if num_classes > 0 else outputs[4]
    class_ids = (
        class_scores.argmax(axis=0)
        if num_classes > 0
        else np.zeros(dim2, dtype=np.int32)
    )

    mask = max_scores > conf_threshold
    if not mask.any():
        return [], [], []

    cx = bbox_raw[0][mask]
    cy = bbox_raw[1][mask]
    bw = bbox_raw[2][mask]
    bh = bbox_raw[3][mask]

    scale_w = orig_w / imgsz
    scale_h = orig_h / imgsz
    x1 = ((cx - bw / 2) * scale_w).clip(0, orig_w)
    y1 = ((cy - bh / 2) * scale_h).clip(0, orig_h)
    w = (bw * scale_w).clip(1, orig_w - x1)
    h = (bh * scale_h).clip(1, orig_h - y1)

    boxes_xywh = [
        [float(x), float(y), float(b), float(hh)] for x, y, b, hh in zip(x1, y1, w, h)
    ]
    scores = [float(s) for s in max_scores[mask]]
    ids = [int(c) for c in class_ids[mask]]

    indices = cv2.dnn.NMSBoxes(boxes_xywh, scores, conf_threshold, nms_threshold)
    if not len(indices):
        return [], [], []

    if isinstance(indices[0], (list, tuple)):
        kept = [int(idx[0]) for idx in indices]
    else:
        kept = [int(idx) for idx in indices.flatten()]

    return (
        [boxes_xywh[i] for i in kept],
        [scores[i] for i in kept],
        [ids[i] for i in kept],
    )


def get_clip_model(model_name: str = "ViT-B-32", pretrained: str = "laion2b_s34b_b79k"):
    import torch
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name, pretrained=pretrained
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    return model, preprocess, tokenizer


_U2NET: cv2.dnn.Net | None = None
_U2NET_IS_LOADED = False


def _get_u2net(
    onnx_model_dir: str = "/app/models",
    repo_id: str = "Heliosoph/u2net-onnx",
    filename: str = "u2netp.onnx",
) -> cv2.dnn.Net | None:
    global _U2NET, _U2NET_IS_LOADED
    if _U2NET_IS_LOADED:
        return _U2NET
    _U2NET_IS_LOADED = True
    try:
        local = hf_download(repo_id, filename, onnx_model_dir)
        _U2NET = cv2.dnn.readNetFromONNX(local)
        logger.info("Loaded U2NetP: %s", local)
    except Exception:
        logger.warning("Failed to load U2NetP segmentation model, skipping")
        _U2NET = None
    return _U2NET


def apply_mask(
    chip_rgb: np.ndarray,
    threshold: float = 0.5,
) -> np.ndarray:
    net = _get_u2net()
    if net is None:
        return chip_rgb

    h, w = chip_rgb.shape[:2]
    blob = cv2.dnn.blobFromImage(
        chip_rgb,
        1 / 255.0,
        (320, 320),
        (0, 0, 0),
        swapRB=True,
        crop=False,
    )
    net.setInput(blob)
    mask = net.forward()  # (1, 1, 320, 320)

    mask = cv2.resize(mask[0, 0], (w, h))
    mask_bin = (mask > threshold).astype(np.float32)

    masked = (chip_rgb.astype(np.float32) * mask_bin[..., None]).astype(np.uint8)
    return masked

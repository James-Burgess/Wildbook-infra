from __future__ import annotations

import base64
import json
import random as _random
import socket
import socketserver
import tempfile
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

import requests

from ...new_ml._core import (
    b64 as _b64,
    load_image_bytes as _load_image_bytes,
    resolve_coco_image as _resolve_coco_image,
)


class _WBIAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_SHARED_IMAGE_DIR, **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


_SHARED_IMAGE_DIR: str | None = None
_SHARED_SERVER_PORT: int | None = None


def _get_container_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    finally:
        s.close()


def _start_file_server(annots: list[dict], tmp_dir: str) -> tuple[int, str]:
    global _SHARED_IMAGE_DIR, _SHARED_SERVER_PORT
    _SHARED_IMAGE_DIR = tmp_dir
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    for a in annots:
        img_bytes = _load_image_bytes(a["uri"])
        (Path(tmp_dir) / f"{a['annot_id']}.jpg").write_bytes(img_bytes)
    server = socketserver.TCPServer(("0.0.0.0", 0), _WBIAHandler)
    _SHARED_SERVER_PORT = server.server_address[1]
    Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.5)
    return _SHARED_SERVER_PORT, _get_container_ip()


def _post(url: str, data: dict, timeout: int = 300) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read())
    return raw.get("response", raw)


def _wrap_uuid(val: str) -> dict:
    return {"__UUID__": val}


def _unwrap_uuid(val) -> str:
    if isinstance(val, dict):
        return str(val.get("__UUID__", val))
    return str(val)


def load_dataset(
    coco_json_path: str,
    coco_images_path: str,
    n_images: int = 10,
    n_query: int = 3,
    seed: int = 42,
) -> list[dict]:
    with open(coco_json_path) as f:
        coco = json.load(f)

    images_by_id = {img["id"]: img for img in coco["images"]}
    annotations = coco.get("annotations", [])

    rng = _random.Random(seed)
    rng.shuffle(annotations)

    selected = []
    for a in annotations[:n_images]:
        img_info = images_by_id.get(a["image_id"], {})
        file_name = img_info.get("file_name", "")
        selected.append(
            {
                "uri": _resolve_coco_image(coco_images_path, file_name),
                "annot_id": a["id"],
                "file_name": file_name,
                "image_id": a["image_id"],
                "bbox": a["bbox"],
                "category_id": a.get("category_id", -1),
                "individual_ids": a.get("individual_ids", []),
            }
        )

    query_indices = set(rng.sample(range(len(selected)), min(n_query, len(selected))))
    for i, img in enumerate(selected):
        img["is_query"] = i in query_indices

    return selected


def identify_wbia(
    images: list[dict],
    wbia_url: str,
    temp_dir: str = "/tmp/kedro_wbia_109",
) -> list[dict]:
    port, host_ip = _start_file_server(images, temp_dir)

    # Phase 1 — upload all images + create all annotations in one batch
    uris = [f"http://{host_ip}:{port}/{a['annot_id']}.jpg" for a in images]
    img_uuids = _post(f"{wbia_url}/api/image/json/", {"image_uri_list": uris})
    img_uuid_strs = [_unwrap_uuid(u) for u in img_uuids]

    annot_uuids = _post(
        f"{wbia_url}/api/annot/json/",
        {
            "image_uuid_list": [_wrap_uuid(u) for u in img_uuid_strs],
            "annot_bbox_list": [a["bbox"] for a in images],
            "annot_theta_list": [0.0] * len(images),
            "annot_species_list": ["zebra_plains"] * len(images),
        },
    )
    annot_uuid_strs = [_unwrap_uuid(u) for u in annot_uuids]
    uuid_to_annot_id = {
        annot_uuid_strs[i]: images[i]["annot_id"] for i in range(len(images))
    }

    results = []
    for qi, img in enumerate(images):
        if not img.get("is_query"):
            results.append(img)
            continue

        jobid = _post(
            f"{wbia_url}/api/engine/query/graph/",
            {
                "query_annot_uuid_list": [_wrap_uuid(annot_uuid_strs[qi])],
                "database_annot_uuid_list": [
                    _wrap_uuid(annot_uuid_strs[i])
                    for i in range(len(images))
                    if i != qi
                ],
                "query_config_dict": {
                    "pipeline": "vsmany",
                    "pipeline_root": "vsmany",
                },
            },
        )

        deadline = time.monotonic() + 600
        scores: dict[int, float] = {}
        while time.monotonic() < deadline:
            result = _post(f"{wbia_url}/api/engine/job/result/", {"jobid": jobid})
            if isinstance(result, dict) and result.get("status") == "completed":
                cm = result.get("json_result", result).get("cm_dict", {})
                if cm:
                    data = next(iter(cm.values()))
                    for du, sc in zip(
                        data.get("dannot_uuid_list", []),
                        data.get("annot_score_list", []),
                    ):
                        uid = _unwrap_uuid(du)
                        scores[uuid_to_annot_id.get(uid, uid)] = float(sc)
                break
            time.sleep(2)

        img["wbia_scores"] = scores
        results.append(img)

    return results


def store_results(identified: list[dict], output_path: str) -> list[dict]:
    summary = []
    for img in identified:
        if not img.get("is_query"):
            continue
        wbia_scores = img.get("wbia_scores", {})
        ranked = sorted(wbia_scores.items(), key=lambda x: -x[1])
        summary.append(
            {
                "query_annot_id": img["annot_id"],
                "uri": img["uri"],
                "bbox": img["bbox"],
                "individual_ids": img.get("individual_ids", []),
                "wbia_ranks": [{"annot_id": aid, "score": sc} for aid, sc in ranked],
            }
        )
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary

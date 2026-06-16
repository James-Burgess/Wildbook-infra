from __future__ import annotations

from ._core import logger, b64, load_image_bytes


def identify(
    images: list[dict],
    database: list[dict],
    wbia_core_url: str,
    identify_config: dict | None = None,
    max_db_entries: int = 30,
) -> list[dict]:
    import requests

    url = f"{wbia_core_url}/api/v1/identify/"
    db_slice = database[:max_db_entries]

    db_entries = []
    for db_img in db_slice:
        img_bytes = load_image_bytes(db_img["uri"])
        db_entries.append(
            {
                "aid": f"coco-annot-{db_img['annot_id']}",
                "image_b64": b64(img_bytes),
                "bbox": db_img["bbox"],
            }
        )

    results = []
    for img in images:
        img_bytes = load_image_bytes(img["uri"])
        for chip in img.get("chips", []):
            if not db_entries:
                chip["hotspotter_scores"] = []
                chip["hotspotter_timing_ms"] = 0
                continue
            r = requests.post(
                url,
                json={
                    "query_image_b64": b64(img_bytes),
                    "query_bbox": chip["bbox"],
                    "database": db_entries,
                    "config": identify_config or {},
                },
                timeout=600,
            )
            r.raise_for_status()
            data = r.json()
            chip["hotspotter_scores"] = (
                data.get("response", {}).get("annot_scores", [])
                if data.get("status") == "completed"
                else []
            )
            chip["hotspotter_timing_ms"] = (
                data.get("response", {}).get("timing_ms", 0)
                if data.get("status") == "completed"
                else 0
            )
        results.append(img)
    return results

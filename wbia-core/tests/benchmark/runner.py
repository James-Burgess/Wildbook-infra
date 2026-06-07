"""Benchmark orchestrator — start targets, run queries, save results."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

from coco.loader import CocoSubset
from targets.base import QueryResult, TargetRunner


def _strip_images(body: dict) -> dict:
    """Return a copy of *body* without base64 image data for disk logging."""
    result: dict[str, Any] = {}
    for k, v in body.items():
        if k in ("query_image_b64",):
            result[k] = f"<base64 {len(v)} bytes>"
        elif k == "database" and isinstance(v, list):
            cleaned = []
            for entry in v:
                e = dict(entry)
                if "image_b64" in e:
                    e["image_b64"] = f"<base64 {len(e['image_b64'])} bytes>"
                cleaned.append(e)
            result[k] = cleaned
        else:
            result[k] = v
    return result


def run_benchmark(
    subset: CocoSubset,
    targets: list[TargetRunner],
    results_dir: str | Path,
    config: dict,
) -> dict:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    (results_dir / "config.json").write_text(
        json.dumps({**subset.config, **config}, indent=2)
    )

    aggregate: dict[str, Any] = {
        "targets": {},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    for target in targets:
        name = target.config.name
        target_dir = results_dir / f"target-{name}"
        target_dir.mkdir(parents=True, exist_ok=True)

        manifest: dict[str, Any] = {
            "target": name,
            "image": target.config.image,
            "container_id": None,
            "started_at": None,
            "finished_at": None,
            "n_queries": len(subset.query_indices),
            "total_timing_ms": 0,
            "errors": [],
        }

        try:
            info = target.start()
            manifest["container_id"] = info.get("container_id", "")
            manifest["started_at"] = info.get("started_at", "")
        except Exception as exc:
            manifest["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            manifest["errors"].append(f"Failed to start: {exc}")
            (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            aggregate["targets"][name] = manifest
            continue

        total_timing = 0.0
        has_target_errors = False

        for qi, query_index in enumerate(subset.query_indices):
            query_dir = target_dir / f"query_{qi:03d}"
            query_dir.mkdir(parents=True, exist_ok=True)

            query_annot = subset.annotations[query_index]
            db_indices = [i for i in range(len(subset.annotations)) if i != query_index]

            database_body = []
            for db_idx in db_indices:
                db_annot = subset.annotations[db_idx]
                database_body.append(
                    {
                        "aid": f"coco-annot-{db_annot.annot_id}",
                        "image_b64": base64.b64encode(db_annot.image).decode("utf-8"),
                        "bbox": list(db_annot.bbox),
                        "theta": 0.0,
                        "name_uuid": None,
                        "species": db_annot.species,
                    }
                )

            request_body = {
                "query_image_b64": base64.b64encode(query_annot.image).decode("utf-8"),
                "query_bbox": list(query_annot.bbox),
                "query_theta": 0.0,
                "query_species": query_annot.species,
                "database": database_body,
                "config": config,
            }

            # Save request metadata (no image data)
            (query_dir / "request.json").write_text(
                json.dumps(_strip_images(request_body), indent=2)
            )

            result: QueryResult = target.run_query(query_index, request_body)

            response_data = {
                "query_index": query_index,
                "error": result.error,
                "response": {
                    "annot_scores": result.annot_scores,
                    "timing_ms": result.timing_ms,
                },
                "raw_response": result.raw_response,
            }
            (query_dir / "response.json").write_text(
                json.dumps(response_data, indent=2)
            )

            if result.error:
                has_target_errors = True
                manifest["errors"].append(f"query_{qi:03d}: {result.error}")
            else:
                total_timing += result.timing_ms

        manifest["total_timing_ms"] = total_timing
        manifest["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        if not getattr(target.config, "keep_containers", False):
            try:
                target.stop()
            except Exception as exc:
                manifest["errors"].append(f"Failed to stop: {exc}")

        aggregate["targets"][name] = manifest

    aggregate["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return aggregate

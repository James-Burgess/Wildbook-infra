#!/usr/bin/env python3
"""Run the same COCO subset through wbia-core and WBIA 10.10 side-by-side.

Produces a rank-order comparison showing agreement between the two pipelines
on the same query/database annotations.

Usage::

    python pipeline/tests/benchmark/compare_1010.py \\
        --wbia-core http://localhost:5001 \\
        --wbia      http://localhost:5000 \\
        --n-annots 6 --n-queries 2 --seed 42

Requires both wbia-core and WBIA containers running.
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import socket
import socketserver
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread


def _resolve_image(coco_images_path: str, file_name: str) -> Path:
    base = Path(coco_images_path)
    for subdir in ("train2020", "val2020", "test2020"):
        candidate = base / subdir / file_name
        if candidate.exists():
            return candidate
    return base / file_name


def _post(url: str, data: dict, timeout: int = 300) -> dict:
    """POST JSON, return unwrapped ``response`` field (WBIA envelope)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
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


def load_coco_subset(
    coco_json_path: str,
    coco_images_path: str,
    n_annots: int = 6,
    n_queries: int = 2,
    seed: int = 42,
) -> list[dict]:
    with open(coco_json_path) as f:
        coco = json.load(f)

    images_by_id = {img["id"]: img for img in coco["images"]}
    annotations = coco.get("annotations", [])

    rng = random.Random(seed)
    rng.shuffle(annotations)

    selected: list[dict] = []
    for a in annotations[:n_annots]:
        img_info = images_by_id.get(a["image_id"], {})
        file_name = img_info.get("file_name", "")
        image_path = _resolve_image(coco_images_path, file_name)
        image_bytes = image_path.read_bytes() if image_path.exists() else b""

        selected.append(
            {
                "aid": f"coco-annot-{a['id']}",
                "annot_id": a["id"],
                "file_name": file_name,
                "image_path": str(image_path),
                "image_bytes": image_bytes,
                "bbox": a["bbox"],
                "individual_ids": a.get("individual_ids", []),
            }
        )

    query_indices = set(rng.sample(range(len(selected)), min(n_queries, len(selected))))
    for i in range(len(selected)):
        selected[i]["is_query"] = i in query_indices

    return selected


# ---- wbia-core query -------------------------------------------------------


def query_wbia_core(
    query: dict,
    database: list[dict],
    wbia_core_url: str,
    config: dict | None = None,
) -> dict[str, float]:
    db_entries = [
        {
            "aid": a["aid"],
            "image_b64": base64.b64encode(a["image_bytes"]).decode(),
            "bbox": a["bbox"],
        }
        for a in database
    ]

    body = {
        "query_image_b64": base64.b64encode(query["image_bytes"]).decode(),
        "query_bbox": query["bbox"],
        "database": db_entries,
        "config": config
        or {
            "K": 4,
            "score_method": "nsum",
            "fg_on": False,
            "sv_on": False,
            "flann_algorithm": "kdtree",
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{wbia_core_url}/api/v1/identify/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = json.loads(resp.read())

    scores: dict[str, float] = {}
    for s in raw.get("response", {}).get("annot_scores", []):
        scores[s["aid"]] = float(s["score"])
    return scores


# ---- WBIA 10.10 multi-step query -------------------------------------------


class _ImageHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/tmp/wbia_compare_1010", **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


def _start_file_server(annots: list[dict]) -> tuple[int, Thread]:
    tmp = Path("/tmp/wbia_compare_1010")
    tmp.mkdir(parents=True, exist_ok=True)
    for a in annots:
        (tmp / f"{a['annot_id']}.jpg").write_bytes(a["image_bytes"])

    server = socketserver.TCPServer(("0.0.0.0", 0), _ImageHandler)
    port = server.server_address[1]
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    return port, t


def query_wbia(
    query: dict,
    database: list[dict],
    wbia_url: str,
    file_server_port: int,
) -> dict[str, float]:
    all_annots = [query] + database
    host_ip = "172.18.0.1"

    uris = [
        f"http://{host_ip}:{file_server_port}/{a['annot_id']}.jpg" for a in all_annots
    ]

    img_uuids = _post(f"{wbia_url}/api/image/json/", {"image_uri_list": uris})
    img_uuid_strs = [_unwrap_uuid(u) for u in img_uuids]

    annot_uuids = _post(
        f"{wbia_url}/api/annot/json/",
        {
            "image_uuid_list": [_wrap_uuid(u) for u in img_uuid_strs],
            "annot_bbox_list": [a["bbox"] for a in all_annots],
            "annot_theta_list": [0.0] * len(all_annots),
            "annot_species_list": ["zebra_plains"] * len(all_annots),
        },
    )
    annot_uuid_strs = [_unwrap_uuid(u) for u in annot_uuids]

    uuid_to_aid = {
        annot_uuid_strs[i]: all_annots[i]["aid"] for i in range(len(all_annots))
    }

    jobid = _post(
        f"{wbia_url}/api/engine/query/graph/",
        {
            "query_annot_uuid_list": [_wrap_uuid(annot_uuid_strs[0])],
            "database_annot_uuid_list": [_wrap_uuid(u) for u in annot_uuid_strs[1:]],
            "query_config_dict": {
                "pipeline": "vsmany",
                "pipeline_root": "vsmany",
            },
        },
    )

    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        result = _post(f"{wbia_url}/api/engine/job/result/", {"jobid": jobid})
        if isinstance(result, dict) and result.get("status") == "completed":
            cm = result.get("json_result", result).get("cm_dict", {})
            if not cm:
                return {}
            data = next(iter(cm.values()))
            scores: dict[str, float] = {}
            for du, sc in zip(
                data.get("dannot_uuid_list", []),
                data.get("annot_score_list", []),
            ):
                uid = _unwrap_uuid(du)
                scores[uuid_to_aid.get(uid, uid)] = float(sc)
            return scores
        time.sleep(2)

    raise TimeoutError("WBIA job did not complete within 600s")


# ---- report ----------------------------------------------------------------


def print_report(
    subset: list[dict],
    core_scores: dict[int, dict[str, float]],
    wbia_scores: dict[int, dict[str, float]],
) -> dict:
    query_indices = [i for i, a in enumerate(subset) if a["is_query"]]

    report: dict = {"config": {}, "queries": []}

    print("=== wbia-core vs WBIA 10.10 Rank Comparison ===\n")

    for qi in query_indices:
        q = subset[qi]
        print(
            f"Query: {q['aid']}  "
            f"(indiv={q['individual_ids'][:3]}...)  "
            f"bbox={[round(x) for x in q['bbox']]}"
        )

        cr = core_scores.get(qi, {})
        core_ranked = sorted(cr.keys(), key=lambda a: -cr[a])

        wr = wbia_scores.get(qi, {})
        wbia_ranked = sorted(wr.keys(), key=lambda a: -wr[a])

        max_ranks = max(len(core_ranked), len(wbia_ranked))
        agreements = 0
        top1_match = False

        header = f"  {'Rank':<6} {'wbia-core':<25} {'score':<10} | {'WBIA 10.10':<25} {'score':<10}"
        sep = f"  {'-'*6} {'-'*25} {'-'*10} | {'-'*25} {'-'*10}"
        print(header)
        print(sep)

        query_entry = {
            "query": q["aid"],
            "individual_ids": q["individual_ids"],
            "bbox": [round(x) for x in q["bbox"]],
            "ranks": [],
        }

        for rank in range(max_ranks):
            ca = core_ranked[rank] if rank < len(core_ranked) else "—"
            cs = f"{cr.get(ca, 0):.2f}" if ca != "—" else "—"
            wa = wbia_ranked[rank] if rank < len(wbia_ranked) else "—"
            ws = f"{wr.get(wa, 0):.2f}" if wa != "—" else "—"
            match = ca == wa
            marker = "*" if match else " "
            if match:
                agreements += 1
                if rank == 0:
                    top1_match = True

            print(f"  {rank+1:<6} {marker}{ca:<24} {cs:<10} | {wa:<25} {ws:<10}")
            query_entry["ranks"].append(
                {
                    "rank": rank + 1,
                    "wbia_core": (
                        {"aid": ca, "score": cr.get(ca)} if ca != "—" else None
                    ),
                    "wbia_1010": (
                        {"aid": wa, "score": wr.get(wa)} if wa != "—" else None
                    ),
                    "match": bool(match),
                }
            )

        query_entry["top1_match"] = top1_match
        query_entry["n_agreements"] = agreements
        query_entry["n_scores_core"] = len(cr)
        query_entry["n_scores_wbia"] = len(wr)
        print()
        report["queries"].append(query_entry)

    # summary
    report["summary"] = {
        "n_queries": len(query_indices),
        "n_top1_agreements": sum(1 for q in report["queries"] if q["top1_match"]),
        "mean_agreements": (
            sum(q["n_agreements"] for q in report["queries"]) / len(query_indices)
            if query_indices
            else 0
        ),
    }

    summary = report["summary"]
    print(
        f"Top-1 agreement: {summary['n_top1_agreements']}/{summary['n_queries']} "
        f"({summary['n_top1_agreements']/summary['n_queries']*100:.0f}%)"
    )
    print(f"Mean rank agreements: {summary['mean_agreements']:.1f}")
    return report


# ---- CLI -------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Compare wbia-core vs WBIA 10.10 on a COCO subset"
    )
    parser.add_argument(
        "--wbia-core",
        default="http://localhost:5001",
        help="wbia-core sidecar URL (default: http://localhost:5001)",
    )
    parser.add_argument(
        "--wbia",
        default="http://localhost:5000",
        help="WBIA 10.10 URL (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--coco-json",
        default="wbia-core/tests/test-dataset/annotations/instances_train2020.json",
        help="Path to COCO JSON annotation file",
    )
    parser.add_argument(
        "--coco-images",
        default="wbia-core/tests/test-dataset/images",
        help="Path to COCO images directory",
    )
    parser.add_argument(
        "--n-annots", type=int, default=6, help="Annotations in subset (default: 6)"
    )
    parser.add_argument(
        "--n-queries",
        type=int,
        default=2,
        help="Query annotations in subset (default: 2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON report to file",
    )
    args = parser.parse_args()

    # Load subset
    subset = load_coco_subset(
        args.coco_json,
        args.coco_images,
        n_annots=args.n_annots,
        n_queries=args.n_queries,
        seed=args.seed,
    )

    query_indices = [i for i, a in enumerate(subset) if a["is_query"]]
    db = [a for a in subset]

    print(
        f"Dataset: {len(subset)} annots, {len(query_indices)} queries, "
        f"seed={args.seed}"
    )
    for i, a in enumerate(subset):
        label = "QUERY" if a["is_query"] else "DB"
        print(f"  [{label:5s}] {a['aid']}  indiv={a['individual_ids'][:3]}...")

    # Start HTTP server for WBIA
    print("\nStarting file server for WBIA image ingestion...")
    port, server_thread = _start_file_server(subset)
    time.sleep(0.5)

    # Run queries
    core_scores: dict[int, dict[str, float]] = {}
    wbia_scores: dict[int, dict[str, float]] = {}

    try:
        for qi in query_indices:
            q = subset[qi]
            q_db = [a for i, a in enumerate(subset) if i != qi]

            print(f"  wbia-core: querying {q['aid']}...")
            core_scores[qi] = query_wbia_core(q, q_db, args.wbia_core)

            print(f"  WBIA 10.10: querying {q['aid']}...")
            try:
                wbia_scores[qi] = query_wbia(q, q_db, args.wbia, port)
            except Exception as exc:
                print(f"  WBIA 10.10: FAILED: {exc}")
                wbia_scores[qi] = {}
    finally:
        # Clean up temp files
        import shutil

        shutil.rmtree("/tmp/wbia_compare_1010", ignore_errors=True)

    # Report
    report = print_report(subset, core_scores, wbia_scores)
    report["config"].update(
        {
            "n_annots": args.n_annots,
            "n_queries": args.n_queries,
            "seed": args.seed,
            "wbia_core_url": args.wbia_core,
            "wbia_url": args.wbia,
        }
    )

    # Write JSON if requested
    json_report = {
        "config": report["config"],
        "summary": report["summary"],
        "queries": report["queries"],
    }
    if args.output:
        output_path = args.output
        with open(output_path, "w") as f:
            json.dump(json_report, f, indent=2)
        print(f"\nJSON report → {output_path}")
    else:
        print(json.dumps(json_report, indent=2))


if __name__ == "__main__":
    main()

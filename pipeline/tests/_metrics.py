from __future__ import annotations

import json
import math
from collections import OrderedDict
from pathlib import Path
from typing import Any


def rank_annot_scores(
    scores: dict[int, float] | list[dict],
) -> list[tuple[int, float]]:
    if isinstance(scores, dict):
        return sorted(scores.items(), key=lambda x: -x[1])
    pairs = []
    for entry in scores:
        aid = entry.get("aid", "")
        if isinstance(aid, str) and aid.startswith("coco-annot-"):
            aid = int(aid.split("-")[-1])
        elif isinstance(aid, int):
            pass
        else:
            continue
        pairs.append((aid, float(entry.get("score", 0))))
    return sorted(pairs, key=lambda x: -x[1])


def top1_agreement(
    ranks_a: list[tuple[int, float]],
    ranks_b: list[tuple[int, float]],
) -> tuple[bool, int | None, int | None]:
    top_a = ranks_a[0][0] if ranks_a else None
    top_b = ranks_b[0][0] if ranks_b else None
    return top_a is not None and top_a == top_b, top_a, top_b


def top3_overlap(
    ranks_a: list[tuple[int, float]],
    ranks_b: list[tuple[int, float]],
) -> float:
    set_a = {r[0] for r in ranks_a[:3]}
    set_b = {r[0] for r in ranks_b[:3]}
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def spearman_rho(
    ranks_a: list[tuple[int, float]],
    ranks_b: list[tuple[int, float]],
) -> float:
    common = {r[0] for r in ranks_a} & {r[0] for r in ranks_b}
    if len(common) < 2:
        return 0.0

    rmap_a = {aid: score for aid, score in ranks_a if aid in common}
    rmap_b = {aid: score for aid, score in ranks_b if aid in common}

    sorted_a = sorted(rmap_a.items(), key=lambda x: -x[1])
    sorted_b = sorted(rmap_b.items(), key=lambda x: -x[1])

    rank_a = {aid: i for i, (aid, _) in enumerate(sorted_a)}
    rank_b = {aid: i for i, (aid, _) in enumerate(sorted_b)}

    n = len(common)
    d2_sum = sum((rank_a[aid] - rank_b[aid]) ** 2 for aid in common)
    return 1.0 - (6.0 * d2_sum) / (n * (n**2 - 1))


def norm_109_results(identified: list[dict]) -> list[dict]:
    out = []
    for img in identified:
        if not img.get("is_query"):
            continue
        scores = img.get("wbia_scores", {})
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        out.append(
            {
                "query_annot_id": img["annot_id"],
                "uri": img["uri"],
                "bbox": img["bbox"],
                "ranks": [{"annot_id": aid, "score": sc} for aid, sc in ranked],
                "individual_ids": img.get("individual_ids", []),
            }
        )
    return out


def norm_1010_results(identified: list[dict]) -> list[dict]:
    out = []
    for img in identified:
        for chip in img.get("chips", []):
            hs = chip.get("hotspotter_scores", [])
            ranked = rank_annot_scores(hs)
            out.append(
                {
                    "query_annot_id": img["annot_id"],
                    "uri": img["uri"],
                    "bbox": chip["bbox"],
                    "ranks": [{"annot_id": aid, "score": sc} for aid, sc in ranked],
                    "individual_ids": img.get("individual_ids", []),
                }
            )
    return out


def compare_queries(
    results_a: list[dict],
    results_b: list[dict],
    label_a: str = "A",
    label_b: str = "B",
) -> dict:
    by_query_a = {r["query_annot_id"]: r for r in results_a}
    by_query_b = {r["query_annot_id"]: r for r in results_b}

    common_queries = sorted(set(by_query_a) & set(by_query_b))
    if not common_queries:
        return {
            "error": "no common queries",
            "top1_agreement": None,
            "top3_overlap_mean": None,
            "spearman_mean": None,
        }

    agreements = 0
    overlaps = []
    rhos = []
    per_query: list[dict] = []

    for qid in common_queries:
        ra = by_query_a[qid]
        rb = by_query_b[qid]
        ranks_a = [(r["annot_id"], r["score"]) for r in ra["ranks"]]
        ranks_b = [(r["annot_id"], r["score"]) for r in rb["ranks"]]

        agree, top_a, top_b = top1_agreement(ranks_a, ranks_b)
        overlap = top3_overlap(ranks_a, ranks_b)
        rho = spearman_rho(ranks_a, ranks_b)

        if agree:
            agreements += 1
        overlaps.append(overlap)
        rhos.append(rho)

        per_query.append(
            {
                "query_annot_id": qid,
                f"top1_{label_a}": top_a,
                f"top1_{label_b}": top_b,
                "top1_agrees": agree,
                "top3_overlap": round(overlap, 3),
                "spearman_rho": round(rho, 3),
            }
        )

    n = len(common_queries)
    return {
        "n_queries": n,
        "top1_agreement": f"{agreements}/{n} ({round(100 * agreements / n, 1)}%)",
        "top3_overlap_mean": round(sum(overlaps) / n, 3),
        "spearman_mean": round(sum(rhos) / n, 3),
        "per_query": per_query,
    }


def save_comparison(path: str | Path, data: Any) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return str(p)

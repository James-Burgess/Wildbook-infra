from __future__ import annotations

import json
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def store_features(images: list[dict], feature_store_csv: str) -> list[dict]:
    Path(feature_store_csv).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for img in images:
        for chip in img.get("chips", []):
            rows.append(
                {
                    "annot_id": img["annot_id"],
                    "bbox": chip["bbox"],
                    "species": chip.get("classification", "")
                    or img.get("classification", ""),
                    "embedding_dim": len(chip.get("embedding", [])),
                    "num_sift_keypoints": chip.get("sift_keypoints", 0),
                    "sift_descriptor_dim": chip.get("sift_descriptor_dim", 0),
                    "clip_embedding_dim": chip.get("clip_embedding_dim", 0),
                }
            )
    if rows:
        with open(feature_store_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    return images


def store_results(identified: list[dict], output_path: str) -> list[dict]:
    summary = []
    for img in identified:
        detect_ms = img.get("detect_timing_ms", 0)
        for chip in img.get("chips", []):
            miewid_dim = len(chip.get("embedding", []))
            clip_dim = chip.get("clip_embedding_dim", 0)
            sift_kp = chip.get("sift_keypoints", 0)
            sift_dim = chip.get("sift_descriptor_dim", 0)
            hs_scores = chip.get("hotspotter_scores", [])
            hs_top = hs_scores[0] if hs_scores else None
            hs_match_count = len([s for s in hs_scores if s.get("score", 0) > 0])

            logger.info(
                "chip [%s] cls=%s(%.3f) detect=%dms | miewid=%dd | clip=%dd | "
                "cv2_sift=%dkp/%dd | hotspotter=%d_matches top=%.4f",
                chip["bbox"],
                chip.get("classification", ""),
                chip.get("classification_score", 0.0),
                detect_ms,
                miewid_dim,
                clip_dim,
                sift_kp,
                sift_dim,
                hs_match_count,
                hs_top["score"] if hs_top else 0.0,
            )

            summary.append(
                {
                    "uri": img["uri"],
                    "bbox": chip["bbox"],
                    "theta": chip.get("theta", 0.0),
                    "score": chip.get("score", 0.0),
                    "classification": chip.get("classification", ""),
                    "classification_score": chip.get("classification_score", 0.0),
                    "embedding": chip.get("embedding", [])[:16],
                    "miewid_dim": miewid_dim,
                    "clip_embedding_dim": clip_dim,
                    "cv2_sift_keypoints": sift_kp,
                    "cv2_sift_descriptor_dim": sift_dim,
                    "extract_timing_ms": chip.get("extract_timing_ms", 0),
                    "detect_timing_ms": detect_ms,
                    "hotspotter_timing_ms": chip.get("hotspotter_timing_ms", 0),
                    "hotspotter_match_count": hs_match_count,
                    "hotspotter_top": hs_top,
                }
            )
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary

from __future__ import annotations

import json
from pathlib import Path

from wildbook_pipeline.pipelines.new_ml.store import store_features, store_results


class TestStoreFeatures:
    def test_writes_csv_with_expected_fields(self, tmp_path):
        csv_path = tmp_path / "features.csv"
        images = [
            {
                "annot_id": 1,
                "chips": [
                    {
                        "bbox": [0, 0, 100, 100],
                        "embedding": [0.1] * 128,
                        "sift_keypoints": 42,
                        "sift_descriptor_dim": 128,
                        "clip_embedding_dim": 512,
                    }
                ],
            }
        ]
        result = store_features(images, csv_path)
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "annot_id" in content
        assert "embedding_dim" in content
        assert "num_sift_keypoints" in content
        assert "42" in content
        assert result is images

    def test_empty_images_skips_write(self, tmp_path):
        csv_path = tmp_path / "features.csv"
        store_features([], csv_path)
        assert not csv_path.exists()

    def test_no_chips_skips_write(self, tmp_path):
        csv_path = tmp_path / "features.csv"
        store_features([{"annot_id": 1, "chips": []}], csv_path)
        assert not csv_path.exists()

    def test_multiple_chips_multiple_images(self, tmp_path):
        csv_path = tmp_path / "features.csv"
        images = [
            {
                "annot_id": 1,
                "chips": [
                    {"bbox": [0, 0, 10, 10], "embedding": [0.1] * 64},
                    {"bbox": [10, 10, 20, 20], "embedding": [0.2] * 64},
                ],
            },
            {
                "annot_id": 2,
                "chips": [
                    {"bbox": [0, 0, 10, 10], "embedding": [0.3] * 64},
                ],
            },
        ]
        store_features(images, csv_path)
        lines = csv_path.read_text().strip().split("\n")
        assert len(lines) == 4  # header + 3 data rows

    def test_creates_parent_directories(self, tmp_path):
        csv_path = tmp_path / "nested" / "deep" / "features.csv"
        store_features(
            [
                {
                    "annot_id": 1,
                    "chips": [{"bbox": [0, 0, 10, 10], "embedding": [0.1] * 64}],
                }
            ],
            csv_path,
        )
        assert csv_path.exists()

    def test_missing_optional_fields_defaults_zero(self, tmp_path):
        csv_path = tmp_path / "features.csv"
        images = [
            {
                "annot_id": 1,
                "chips": [
                    {"bbox": [0, 0, 10, 10], "embedding": [0.1] * 64},
                ],
            }
        ]
        store_features(images, csv_path)
        content = csv_path.read_text()
        assert "0" in content


class TestStoreResults:
    def test_writes_json_with_expected_fields(self, tmp_path):
        json_path = tmp_path / "results.json"
        identified = [
            {
                "uri": "test.jpg",
                "chips": [
                    {
                        "bbox": [0, 0, 100, 100],
                        "theta": 0.0,
                        "score": 0.95,
                        "classification": "zebra",
                        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 50,
                        "sift_keypoints": 42,
                        "sift_descriptor_dim": 128,
                        "clip_embedding_dim": 512,
                        "extract_timing_ms": 100,
                        "hotspotter_timing_ms": 200,
                        "hotspotter_scores": [
                            {"aid": "coco-annot-1", "score": 0.98},
                            {"aid": "coco-annot-2", "score": 0.12},
                        ],
                    }
                ],
                "detect_timing_ms": 50,
            }
        ]
        result = store_results(identified, json_path)
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert len(data) == 1
        entry = data[0]
        assert entry["uri"] == "test.jpg"
        assert entry["bbox"] == [0, 0, 100, 100]
        assert entry["classification"] == "zebra"
        assert entry["hotspotter_top"]["aid"] == "coco-annot-1"
        assert entry["cv2_sift_keypoints"] == 42
        assert entry["hotspotter_timing_ms"] == 200
        assert entry["detect_timing_ms"] == 50

    def test_empty_identified(self, tmp_path):
        json_path = tmp_path / "results.json"
        result = store_results([], json_path)
        assert json_path.exists()
        assert json.loads(json_path.read_text()) == []

    def test_no_hotspotter_scores(self, tmp_path):
        json_path = tmp_path / "results.json"
        identified = [
            {
                "uri": "test.jpg",
                "chips": [
                    {
                        "bbox": [0, 0, 100, 100],
                        "theta": 0.0,
                        "score": 0.95,
                        "embedding": [0.1] * 128,
                    }
                ],
                "detect_timing_ms": 0,
            }
        ]
        store_results(identified, json_path)
        data = json.loads(json_path.read_text())
        assert data[0]["hotspotter_top"] is None
        assert data[0]["hotspotter_match_count"] == 0

    def test_no_chips_omits_entry(self, tmp_path):
        json_path = tmp_path / "results.json"
        identified = [{"uri": "test.jpg", "detect_timing_ms": 0, "chips": []}]
        store_results(identified, json_path)
        assert json.loads(json_path.read_text()) == []

    def test_mutates_in_place(self, tmp_path):
        json_path = tmp_path / "results.json"
        identified = [{"uri": "test.jpg", "detect_timing_ms": 0, "chips": []}]
        result = store_results(identified, json_path)
        assert result is not identified

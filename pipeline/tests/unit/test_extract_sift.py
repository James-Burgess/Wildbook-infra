from __future__ import annotations

import numpy as np
import pytest

from wildbook_pipeline.pipelines.new_ml.extract_sift import extract_hotspotter_sift


def _make_test_image(path: str, size: tuple = (200, 200)):
    import cv2

    img = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    cv2.imwrite(path, img)


class TestExtractHotspotterSift:
    def test_extracts_keypoints_from_chip(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path)
        images = [
            {
                "uri": img_path,
                "chips": [
                    {"bbox": [10, 10, 100, 100], "theta": 0.0, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        chip = result[0]["chips"][0]
        assert "sift_keypoints" in chip
        assert chip["sift_keypoints"] >= 0
        assert "sift_descriptors" in chip
        assert "sift_descriptor_dim" in chip

    def test_descriptors_have_128_dim(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path)
        images = [
            {
                "uri": img_path,
                "chips": [
                    {"bbox": [0, 0, 200, 200], "theta": 0.0, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        chip = result[0]["chips"][0]
        if chip["sift_keypoints"] > 0:
            assert len(chip["sift_descriptors"][0]) == 128
            assert chip["sift_descriptor_dim"] == 128

    def test_empty_chips(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path)
        images = [{"uri": img_path, "chips": []}]
        result = extract_hotspotter_sift(images)
        assert len(result[0]["chips"]) == 0

    def test_missing_image_skips_gracefully(self, tmp_path):
        images = [
            {
                "uri": str(tmp_path / "nonexistent.jpg"),
                "chips": [
                    {"bbox": [10, 10, 100, 100], "theta": 0.0, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        assert len(result[0]["chips"]) == 1

    def test_multiple_chips_per_image(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path, (300, 300))
        images = [
            {
                "uri": img_path,
                "chips": [
                    {"bbox": [0, 0, 100, 100], "theta": 0.0, "score": 1.0},
                    {"bbox": [100, 100, 100, 100], "theta": 0.0, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        chips = result[0]["chips"]
        assert len(chips) == 2
        for c in chips:
            assert "sift_keypoints" in c

    def test_rotated_chip_still_works(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path, (200, 200))
        images = [
            {
                "uri": img_path,
                "chips": [
                    {"bbox": [50, 50, 100, 100], "theta": 0.5, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        chip = result[0]["chips"][0]
        assert chip["sift_keypoints"] >= 0

    def test_mutates_in_place(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        _make_test_image(img_path)
        images = [
            {
                "uri": img_path,
                "chips": [
                    {"bbox": [10, 10, 100, 100], "theta": 0.0, "score": 1.0},
                ],
            }
        ]
        result = extract_hotspotter_sift(images)
        assert result is images

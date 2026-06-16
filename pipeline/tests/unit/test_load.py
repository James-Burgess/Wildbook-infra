from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from wildbook_pipeline.pipelines.new_ml._core import resolve_coco_image
from wildbook_pipeline.pipelines.new_ml.load import load_from_url


class TestLoadFromUrl:
    def make_coco(self, tmp_path, n_annots=3):
        json_path = str(tmp_path / "coco.json")
        images = [{"id": i, "file_name": f"{i:012d}.jpg"} for i in range(n_annots)]
        annotations = [
            {"id": i * 10, "image_id": i, "bbox": [0, 0, 100, 100], "category_id": 1}
            for i in range(n_annots)
        ]
        data = {"images": images, "annotations": annotations}
        with open(json_path, "w") as f:
            json.dump(data, f)
        return json_path, images, annotations

    def test_loads_annotations(self, tmp_path):
        json_path, images, annotations = self.make_coco(tmp_path)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        assert len(result) == 3

    def test_each_annotation_has_expected_keys(self, tmp_path):
        json_path, _, _ = self.make_coco(tmp_path)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        for item in result:
            assert "uri" in item
            assert "annot_id" in item
            assert "file_name" in item
            assert "image_id" in item
            assert "bbox" in item
            assert "category_id" in item
            assert "individual_ids" in item

    def test_annot_id_from_coco(self, tmp_path):
        json_path, _, annotations = self.make_coco(tmp_path)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        for i, item in enumerate(result):
            assert item["annot_id"] == annotations[i]["id"]

    def test_respects_limit_of_10(self, tmp_path):
        json_path, _, _ = self.make_coco(tmp_path, n_annots=20)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        assert len(result) == 10

    def test_no_annotations_returns_empty(self, tmp_path):
        json_path = str(tmp_path / "coco.json")
        with open(json_path, "w") as f:
            json.dump({"images": [], "annotations": []}, f)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        assert result == []

    def test_missing_image_id_raises_key_error(self, tmp_path):
        json_path = str(tmp_path / "coco.json")
        with open(json_path, "w") as f:
            json.dump({"images": [], "annotations": [{"id": 0, "image_id": 999}]}, f)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            with pytest.raises(KeyError):
                load_from_url(json_path, str(tmp_path), json_path)

    def test_initial_limit_slice_applied(self, tmp_path):
        json_path, _, _ = self.make_coco(tmp_path, n_annots=5)
        with patch(
            "wildbook_pipeline.pipelines.new_ml.load.resolve_coco_image",
            return_value="dummy.jpg",
        ):
            result = load_from_url(json_path, str(tmp_path), json_path)
        assert len(result) == 5

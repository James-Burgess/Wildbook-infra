"""Tests for the COCO subset loader."""

from pathlib import Path

from tests.benchmark.coco.loader import CocoLoader

COCO_JSON = Path("tests/test-dataset/annotations/instances_train2020.json")
IMAGE_DIR = Path("tests/test-dataset/images/train2020/")


class TestCocoLoader:
    def test_loads_json(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        assert len(loader._raw.get("annotations", [])) == 6925

    def test_select_subset_default(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        subset = loader.select_subset()
        assert len(subset.annotations) == 100
        assert len(subset.query_indices) == 10
        assert subset.config["n_annots"] == 100
        assert subset.config["n_queries"] == 10
        assert subset.config["species"] is None
        assert subset.config["seed"] == 42

    def test_select_subset_species_filter(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        subset = loader.select_subset(n_annots=200, species="zebra_plains")
        assert len(subset.annotations) == 200
        for ann in subset.annotations:
            assert ann.species == "zebra_plains"

    def test_select_subset_deterministic(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        a = loader.select_subset(seed=42)
        b = loader.select_subset(seed=42)
        a_ids = [ann.annot_id for ann in a.annotations]
        b_ids = [ann.annot_id for ann in b.annotations]
        assert a_ids == b_ids

    def test_select_subset_different_seed(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        a = loader.select_subset(seed=42)
        b = loader.select_subset(seed=99)
        a_ids = [ann.annot_id for ann in a.annotations]
        b_ids = [ann.annot_id for ann in b.annotations]
        assert a_ids != b_ids

    def test_select_subset_n_queries(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        subset = loader.select_subset(n_queries=5)
        assert len(subset.query_indices) == 5
        assert subset.config["n_queries"] == 5

    def test_select_subset_images_loaded(self):
        loader = CocoLoader(COCO_JSON, IMAGE_DIR)
        subset = loader.select_subset(n_annots=10)
        for ann in subset.annotations:
            assert len(ann.image) > 0
            assert ann.image[:2] == b"\xff\xd8"  # JPEG magic bytes

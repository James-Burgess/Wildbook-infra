from __future__ import annotations

from wildbook_pipeline.pipelines.new_ml.classify import classify, notify


class TestClassify:
    DEFAULT_LABELS = ["plains_zebra", "grevys_zebra"]

    def test_empty_list(self):
        assert classify([], self.DEFAULT_LABELS) == []

    def test_no_detections_no_clip(self):
        images = [{"uri": "test.jpg", "detections": {}}]
        result = classify(images, self.DEFAULT_LABELS)
        assert result[0]["detections"]["classifications"] == []

    def test_unknown_when_no_clip_embedding(self):
        images = [
            {
                "uri": "test.jpg",
                "detections": {"clip_embeddings": [{"embedding": [], "dim": 0}]},
            }
        ]
        result = classify(images, self.DEFAULT_LABELS)
        assert result[0]["detections"]["classifications"][0]["species"] == "unknown"
        assert result[0]["detections"]["classifications"][0]["score"] == 0.0

    def test_multiple_images(self):
        images = [
            {"uri": "a.jpg", "detections": {}},
            {"uri": "b.jpg", "detections": {}},
        ]
        result = classify(images, self.DEFAULT_LABELS)
        assert len(result) == 2
        for img in result:
            assert "classifications" in img["detections"]

    def test_mutates_in_place(self):
        images = [{"uri": "test.jpg", "detections": {}}]
        result = classify(images, self.DEFAULT_LABELS)
        assert result is images


class TestNotify:
    def test_returns_input(self):
        data = [{"id": 1}]
        assert notify(data) is data

    def test_empty_list(self):
        assert notify([]) == []

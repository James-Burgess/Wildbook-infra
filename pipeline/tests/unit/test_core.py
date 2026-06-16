from __future__ import annotations

import numpy as np
import pytest

from wildbook_pipeline.pipelines.new_ml._core import (
    b64,
    extract_chip,
    parse_yolo_output,
    resolve_coco_image,
)


class TestB64:
    def test_encodes_bytes(self):
        result = b64(b"hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_bytes(self):
        result = b64(b"")
        assert isinstance(result, str)

    def test_image_jpeg(self):
        result = b64(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        assert "/8" in result or "AA" in result


class TestResolveCocoImage:
    def test_returns_path_as_is_when_not_resolvable(self, tmp_path):
        result = resolve_coco_image(str(tmp_path), "train2020/000000000000.jpg")
        assert result == str(tmp_path / "train2020/000000000000.jpg")

    def test_prefers_train2020(self, tmp_path):
        for subdir in ("train2020", "val2020", "test2020"):
            (tmp_path / subdir).mkdir()
        (tmp_path / "train2020" / "img.jpg").write_text("fake")
        result = resolve_coco_image(str(tmp_path), "img.jpg")
        assert result == str(tmp_path / "train2020" / "img.jpg")

    def test_falls_back_to_val2020(self, tmp_path):
        for subdir in ("train2020", "val2020", "test2020"):
            (tmp_path / subdir).mkdir()
        (tmp_path / "val2020" / "img.jpg").write_text("fake")
        result = resolve_coco_image(str(tmp_path), "img.jpg")
        assert result == str(tmp_path / "val2020" / "img.jpg")

    def test_falls_back_to_test2020(self, tmp_path):
        for subdir in ("train2020", "val2020", "test2020"):
            (tmp_path / subdir).mkdir()
        (tmp_path / "test2020" / "img.jpg").write_text("fake")
        result = resolve_coco_image(str(tmp_path), "img.jpg")
        assert result == str(tmp_path / "test2020" / "img.jpg")

    def test_resolve_with_file_name_in_subdir(self, tmp_path):
        (tmp_path / "train2020").mkdir()
        (tmp_path / "train2020" / "000000000000.jpg").write_text("fake")
        result = resolve_coco_image(str(tmp_path), "000000000000.jpg")
        assert "train2020" in result


class TestExtractChip:
    def test_axis_aligned_box(self):
        rgb = np.zeros((200, 200, 3), dtype=np.uint8)
        rgb[50:150, 50:150] = 255
        chip = extract_chip(rgb, [50, 50, 100, 100], 0.0)
        assert chip.shape == (100, 100, 3)
        assert chip[0, 0].tolist() == [255, 255, 255]

    def test_chip_at_boundary_clipped(self):
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        chip = extract_chip(rgb, [-10, -10, 200, 200], 0.0)
        assert chip.shape[0] <= 100
        assert chip.shape[1] <= 100

    def test_rotated_box_returns_image(self):
        rgb = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        chip = extract_chip(rgb, [50, 50, 100, 100], 0.3)
        assert chip.ndim == 3
        assert chip.shape[2] == 3
        assert chip.size > 0

    def test_zero_rotation_same_as_crop(self):
        rgb = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
        chip = extract_chip(rgb, [100, 100, 50, 50], 0.0)
        expected = rgb[100:150, 100:150]
        assert chip.shape == expected.shape

    def test_negative_bbox_values(self):
        rgb = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        chip = extract_chip(rgb, [-5, -5, 20, 20], 0.0)
        assert chip.shape[0] > 0
        assert chip.shape[1] > 0

    def test_bbox_exceeds_image(self):
        rgb = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        chip = extract_chip(rgb, [80, 80, 100, 100], 0.0)
        assert chip.shape[0] == 20
        assert chip.shape[1] == 20


class TestParseYoloOutput:
    def test_empty_output(self):
        outputs = np.zeros((1, 0, 4), dtype=np.float32)
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_pre_filtered_format(self):
        outputs = np.zeros((1, 300, 4), dtype=np.float32)
        outputs[0, 0] = [0.5, 0.5, 0.3, 0.3]
        outputs[0, 1] = [0.2, 0.3, 0.1, 0.2]
        outputs[0, 2] = [10.0, 10.0, 20.0, 20.0]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        filtered = [b for b in bboxes if b[2] * b[3] > 0]
        assert len(filtered) <= 3

    def test_pre_filtered_large_area_only(self):
        outputs = np.zeros((1, 300, 4), dtype=np.float32)
        outputs[0, 0] = [0.5, 0.5, 0.001, 0.001]
        outputs[0, 1] = [0.5, 0.5, 0.5, 0.5]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) <= 1

    def test_nms_deduplicates(self):
        outputs = np.zeros((1, 300, 4), dtype=np.float32)
        outputs[0, 0] = [0.5, 0.5, 0.3, 0.3]
        outputs[0, 1] = [0.51, 0.51, 0.29, 0.29]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.1)
        assert len(bboxes) == 1

    def test_zero_outputs(self):
        bboxes, scores, ids = parse_yolo_output(
            np.zeros((1, 0, 4)), 640, 480, 640, 0.25, 0.45
        )
        assert len(bboxes) == 0

    def test_standard_format_below_threshold(self):
        n_classes = 80
        n_dets = 100
        outputs = np.zeros((1, n_classes + 4, n_dets), dtype=np.float32)
        outputs[0, 4:, :] = 0.01
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_standard_format_with_detections(self):
        n_classes = 80
        n_dets = 10
        outputs = np.zeros((1, n_classes + 4, n_dets), dtype=np.float32)
        outputs[0, 4, 0] = 0.9
        outputs[0, 4, 1] = 0.8
        outputs[0, :4, 0] = [0.5, 0.5, 0.3, 0.3]
        outputs[0, :4, 1] = [0.2, 0.2, 0.1, 0.1]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) >= 1

    def test_tuple_input(self):
        outputs = (np.zeros((1, 0, 4), dtype=np.float32),)
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_list_input(self):
        outputs = [np.zeros((1, 0, 4), dtype=np.float32)]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_2d_batch_dim_missing(self):
        outputs = np.zeros((0, 4), dtype=np.float32)
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_wrong_ndim(self):
        outputs = np.zeros((1, 2, 3, 4, 5), dtype=np.float32)
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

    def test_nms_keeps_separate_boxes(self):
        outputs = np.zeros((1, 300, 4), dtype=np.float32)
        outputs[0, 0] = [0.1, 0.1, 0.05, 0.05]
        outputs[0, 1] = [0.8, 0.8, 0.05, 0.05]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 2

    def test_small_bboxes_filtered_by_min_area(self):
        outputs = np.zeros((1, 300, 4), dtype=np.float32)
        outputs[0, 0] = [0.5, 0.5, 0.0001, 0.0001]
        bboxes, scores, ids = parse_yolo_output(outputs, 640, 480, 640, 0.25, 0.45)
        assert len(bboxes) == 0

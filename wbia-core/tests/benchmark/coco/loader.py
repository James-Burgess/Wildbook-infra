"""COCO dataset loader — reads standard COCO JSON + images and produces subsets."""

from __future__ import annotations

import base64
import json
import pathlib
import random
from dataclasses import dataclass, field

SPECIES_MAP = {
    0: "giraffe_masai",
    1: "zebra_plains",
}


@dataclass
class CocoAnnotation:
    annot_id: int
    image_id: int
    bbox: tuple[int, int, int, int]
    species: str
    individual_ids: list[str]
    image: bytes
    width: int
    height: int


@dataclass
class CocoSubset:
    annotations: list[CocoAnnotation]
    query_indices: list[int]
    config: dict = field(default_factory=dict)


class CocoLoader:
    """Load COCO JSON and images, then select subsets for benchmarking."""

    def __init__(
        self,
        coco_json_path: str | pathlib.Path,
        coco_images_path: str | pathlib.Path,
    ):
        self._images_path = pathlib.Path(coco_images_path)
        with open(coco_json_path) as f:
            self._raw = json.load(f)

        self._cat_name_by_id: dict[int, str] = {}
        for cat in self._raw.get("categories", []):
            self._cat_name_by_id[cat["id"]] = cat["name"]

        self._images_by_id: dict[int, dict] = {}
        for img in self._raw.get("images", []):
            self._images_by_id[img["id"]] = img

    def select_subset(
        self,
        n_annots: int = 100,
        species: str | None = None,
        seed: int = 42,
        n_queries: int = 10,
    ) -> CocoSubset:
        rng = random.Random(seed)

        raw_annots = list(self._raw.get("annotations", []))
        if species:
            raw_annots = [
                a
                for a in raw_annots
                if self._cat_name_by_id.get(a.get("category_id", -1), "") == species
            ]

        rng.shuffle(raw_annots)
        raw_annots = raw_annots[:n_annots]

        annotations: list[CocoAnnotation] = []
        for a in raw_annots:
            img_info = self._images_by_id.get(a["image_id"], {})
            img_path = self._resolve_image(img_info.get("file_name", ""))
            image_bytes = img_path.read_bytes() if img_path.exists() else b""

            attrs = a.get("attributes", {}) or {}
            individual_ids = attrs.get("individual_ids", [])

            cat_id = a.get("category_id", -1)
            species_name = self._cat_name_by_id.get(cat_id, "")

            bbox_raw = a.get("bbox", [0, 0, 0, 0])
            bbox = (
                int(bbox_raw[0]),
                int(bbox_raw[1]),
                int(bbox_raw[2]),
                int(bbox_raw[3]),
            )

            annotations.append(
                CocoAnnotation(
                    annot_id=a["id"],
                    image_id=a["image_id"],
                    bbox=bbox,
                    species=species_name,
                    individual_ids=individual_ids,
                    image=image_bytes,
                    width=img_info.get("width", 0),
                    height=img_info.get("height", 0),
                )
            )

        if len(annotations) < n_queries:
            n_queries = len(annotations)

        indices = list(range(len(annotations)))
        rng.shuffle(indices)
        query_indices = sorted(indices[:n_queries])

        return CocoSubset(
            annotations=annotations,
            query_indices=query_indices,
            config={
                "n_annots": len(annotations),
                "n_queries": n_queries,
                "species": species,
                "seed": seed,
            },
        )

    def _resolve_image(self, file_name: str) -> pathlib.Path:
        for subdir in ["train2020", "val2020", "test2020"]:
            candidate = self._images_path / subdir / file_name
            if candidate.exists():
                return candidate
        return self._images_path / file_name

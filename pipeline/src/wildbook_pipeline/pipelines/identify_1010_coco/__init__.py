from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from ..identify.nodes import (
    extract_miewid,
    identify_hotspotter,
    load_dataset as _load_identify,
    store_results,
)

from .nodes import prepare_coco_bboxes


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=_load_identify,
                inputs=[
                    "params:coco_json_path",
                    "params:coco_images_path",
                    "params:n_images",
                    "params:n_query",
                    "params:seed",
                ],
                outputs="images_coco",
                name="load_coco_node",
            ),
            node(
                func=prepare_coco_bboxes,
                inputs=["images_coco"],
                outputs="images_with_bboxes_coco",
                name="prepare_coco_bboxes_node",
            ),
            node(
                func=extract_miewid,
                inputs=[
                    "images_with_bboxes_coco",
                    "params:ml_service_url",
                    "params:extract_model_id",
                ],
                outputs="images_with_embeddings_coco",
                name="extract_miewid_coco_node",
            ),
            node(
                func=identify_hotspotter,
                inputs=[
                    "images_with_embeddings_coco",
                    "images_coco",
                    "params:wbia_core_url",
                    "params:identify_config",
                    "params:max_db_entries",
                ],
                outputs="identified_coco",
                name="identify_hotspotter_coco_node",
            ),
            node(
                func=store_results,
                inputs=["identified_coco", "params:output_path_coco"],
                outputs="results_coco",
                name="store_coco_node",
            ),
        ],
        tags="identify_1010_coco",
    )

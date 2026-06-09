from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    detect,
    extract_miewid,
    identify_hotspotter,
    load_dataset,
    store_results,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=load_dataset,
                inputs=[
                    "params:coco_json_path",
                    "params:coco_images_path",
                    "params:n_images",
                    "params:n_query",
                    "params:seed",
                ],
                outputs="images",
                name="load_dataset_node",
            ),
            node(
                func=detect,
                inputs=[
                    "images",
                    "params:ml_service_url",
                    "params:predict_model_id",
                    "params:predict_params",
                ],
                outputs="images_with_detections",
                name="detect_node",
            ),
            node(
                func=extract_miewid,
                inputs=[
                    "images_with_detections",
                    "params:ml_service_url",
                    "params:extract_model_id",
                ],
                outputs="images_with_embeddings",
                name="extract_miewid_node",
            ),
            node(
                func=identify_hotspotter,
                inputs=[
                    "images_with_embeddings",
                    "images",
                    "params:wbia_core_url",
                    "params:identify_config",
                    "params:max_db_entries",
                ],
                outputs="identified",
                name="identify_hotspotter_node",
            ),
            node(
                func=store_results,
                inputs=["identified", "params:output_path"],
                outputs="results",
                name="store_results_node",
            ),
        ],
        tags="identify",
    )

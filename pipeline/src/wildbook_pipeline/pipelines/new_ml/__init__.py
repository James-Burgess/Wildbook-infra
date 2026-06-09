from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    classify,
    detect,
    extract_hotspotter_sift,
    extract_miewid,
    identify,
    load_from_url,
    minio_sensor,
    notify,
    store_features,
    store_results,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=minio_sensor,
                inputs=["params:coco_json_path"],
                outputs="raw_images",
                name="minio_sensor_node",
            ),
            node(
                func=load_from_url,
                inputs=[
                    "raw_images",
                    "params:coco_images_path",
                    "params:coco_json_path",
                ],
                outputs="images_newml",
                name="load_from_url_node",
            ),
            node(
                func=detect,
                inputs=[
                    "images_newml",
                    "params:ml_service_url",
                    "params:predict_model_id",
                    "params:predict_params",
                ],
                outputs="images_detected_newml",
                name="detect_newml_node",
            ),
            node(
                func=classify,
                inputs=["images_detected_newml"],
                outputs="images_classified_newml",
                name="classify_newml_node",
            ),
            node(
                func=extract_miewid,
                inputs=[
                    "images_classified_newml",
                    "params:ml_service_url",
                    "params:extract_model_id",
                ],
                outputs="images_embedded_newml",
                name="extract_miewid_newml_node",
            ),
            node(
                func=extract_hotspotter_sift,
                inputs=["images_embedded_newml"],
                outputs="images_sift_newml",
                name="extract_sift_newml_node",
            ),
            node(
                func=store_features,
                inputs=[
                    "images_sift_newml",
                    "params:feature_store_csv",
                ],
                outputs="stored_features_newml",
                name="store_features_newml_node",
            ),
            node(
                func=identify,
                inputs=[
                    "stored_features_newml",
                    "images_newml",
                    "params:wbia_core_url",
                    "params:identify_config",
                    "params:max_db_entries",
                ],
                outputs="identified_newml",
                name="identify_newml_node",
            ),
            node(
                func=store_results,
                inputs=["identified_newml", "params:output_path_newml"],
                outputs="results_newml",
                name="store_newml_node",
            ),
            node(
                func=notify,
                inputs=["identified_newml"],
                outputs="notification_newml",
                name="notify_newml_node",
            ),
        ],
        tags="new_ml",
    )

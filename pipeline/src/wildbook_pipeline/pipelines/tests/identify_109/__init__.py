from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import identify_wbia, load_dataset, store_results


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
                outputs="images_109",
                name="load_109_node",
            ),
            node(
                func=identify_wbia,
                inputs=["images_109", "params:wbia_url"],
                outputs="identified_109",
                name="identify_wbia_node",
            ),
            node(
                func=store_results,
                inputs=["identified_109", "params:output_path_109"],
                outputs="results_109",
                name="store_109_node",
            ),
        ],
        tags="identify_109",
    )

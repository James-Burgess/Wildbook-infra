from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import extract_features, generate_report, load_raw_images, preprocess_images


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=load_raw_images,
                inputs="params:images_path",
                outputs="raw_images",
                name="load_images_node",
            ),
            node(
                func=preprocess_images,
                inputs="raw_images",
                outputs="preprocessed_images",
                name="preprocess_node",
            ),
            node(
                func=extract_features,
                inputs="preprocessed_images",
                outputs="features",
                name="extract_features_node",
            ),
            node(
                func=generate_report,
                inputs="features",
                outputs="report",
                name="generate_report_node",
            ),
        ],
        tags="example",
    )

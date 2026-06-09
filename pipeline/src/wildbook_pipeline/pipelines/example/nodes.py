from __future__ import annotations

import pandas as pd


def load_raw_images(images_path: str) -> pd.DataFrame:
    return pd.read_csv(images_path)


def preprocess_images(raw_images: pd.DataFrame) -> pd.DataFrame:
    df = raw_images.copy()
    df.dropna(inplace=True)
    df["filename"] = df["filename"].str.strip()
    return df


def extract_features(preprocessed_images: pd.DataFrame) -> pd.DataFrame:
    df = preprocessed_images.copy()
    df["feature_vector"] = df["filename"].apply(lambda x: [len(x), hash(x) % 1000])
    return df


def generate_report(features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy()
    df["report"] = df.apply(
        lambda row: f"{row['filename']}: {len(row['feature_vector'])} dims",
        axis=1,
    )
    return df

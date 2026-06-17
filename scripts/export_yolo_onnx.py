#!/usr/bin/env python3
"""Export ultralytics YOLO models to ONNX for opencv5 DNN inference.

Usage::

    python scripts/export_yolo_onnx.py [--model yolo11n] [--imgsz 640] [--opset 12]

Output is written to ``scripts/models/yolo11n.onnx`` by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"


def export_yolo(model_name: str = "yolo11n", imgsz: int = 640, opset: int = 12) -> Path:
    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(f"{model_name}.pt")
    output = model.export(format="onnx", imgsz=imgsz, opset=opset)

    dest = MODELS_DIR / f"{model_name}.onnx"
    Path(output).rename(dest)

    size_mb = dest.stat().st_size / 1_048_576
    print(f"Exported {model_name} → {dest} ({size_mb:.1f} MB)")
    return dest


def main():
    parser = argparse.ArgumentParser(description="Export YOLO model to ONNX")
    parser.add_argument("--model", default="yolo11n", help="YOLO model name")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--opset", type=int, default=12, help="ONNX opset version")
    args = parser.parse_args()
    export_yolo(args.model, args.imgsz, args.opset)


if __name__ == "__main__":
    main()

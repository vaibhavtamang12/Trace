from __future__ import annotations

import argparse
from pathlib import Path

from recommendation_platform.models.recommender import RecommendationModel


def export(model_path: Path, output_path: Path) -> str:
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:
        raise SystemExit(
            "Install the optional ONNX dependencies with: pip install skl2onnx onnx"
        ) from exc
    model = RecommendationModel.load(model_path)
    initial_type = [("features", FloatTensorType([None, len(model.feature_columns)]))]
    onnx_model = convert_sklearn(model.estimator, initial_types=initial_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(onnx_model.SerializeToString())
    return str(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, default=Path("data/processed/model.joblib"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/model.onnx"))
    args = parser.parse_args()
    print(export(args.model_path, args.output))


if __name__ == "__main__":
    main()

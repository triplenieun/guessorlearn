"""Serve the local preprocessing benchmark and save reproducible run results."""

import argparse
import base64
import csv
import io
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
import torch
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from PIL import Image

from model_inference import label as model_labels
from model_inference import load_model
from vector_to_image import transformer_vec_img


ROOT = Path(__file__).resolve().parent
WORK_DIR = ROOT / "project_env" / "benchmark"
ARMS = ("vector", "png")
CANVAS_SIZE = (512, 512)
INPUT_SIZE = (64, 64)


def vector_input(strokes):
    if not isinstance(strokes, list) or not strokes:
        raise ValueError("Expected at least one stroke.")
    scaled = []
    for stroke in strokes:
        if (
            not isinstance(stroke, list) or len(stroke) != 2
            or not all(isinstance(axis, list) for axis in stroke)
            or not stroke[0] or len(stroke[0]) != len(stroke[1])
        ):
            raise ValueError("Each stroke must have matching x and y coordinates.")
        if any(type(point) is not int or not 0 <= point < 512 for axis in stroke for point in axis):
            raise ValueError("Stroke coordinates must be integer canvas pixels.")
        scaled.append([[int(point / 2) for point in axis] for axis in stroke])
    return transformer_vec_img(scaled)


def png_input(data):
    with Image.open(io.BytesIO(data), formats=("PNG",)) as image:
        if image.size != CANVAS_SIZE:
            raise ValueError("Expected a 512 × 512 canvas PNG.")
        grayscale = image.convert("L").resize(INPUT_SIZE, Image.Resampling.BOX)
        pixels = np.asarray(grayscale, dtype=np.float32)
    return ((255.0 - pixels) / 255.0)[None, None]


def input_preview(pixels):
    white_background = np.rint(255 * (1.0 - pixels[0, 0])).astype(np.uint8)
    encoded = io.BytesIO()
    Image.fromarray(white_background).save(encoded, format="PNG")
    return "data:image/png;base64," + base64.b64encode(encoded.getvalue()).decode("ascii")


def predict_top_five(model, pixels):
    with torch.inference_mode():
        output = model(torch.from_numpy(pixels).float())
        probabilities, indices = torch.topk(output.softmax(dim=1), 5, dim=1)
    return [
        {
            "index": index,
            "label": model_labels[index] if index < len(model_labels) else f"미등록 #{index}",
            "probability": probability,
        }
        for index, probability in zip(indices[0].tolist(), probabilities[0].tolist())
    ]


def expected_rows(dataset):
    return {
        (sample["id"], stroke): {
            "id": sample["id"], "label": sample["label"], "stroke": stroke,
            "final": stroke == len(sample["strokes"]),
        }
        for sample in dataset["samples"]
        for stroke in range(1, len(sample["strokes"]) + 1)
    }


def successful(arm):
    return arm is not None and not arm.get("error")


def evaluated_rows(expected, submitted):
    measured = {}
    for row in submitted:
        key = (row["id"], row["stroke"])
        if key not in expected or key in measured:
            raise ValueError(f"Unexpected or duplicate sample and stroke: {key}.")
        if row["label"] != expected[key]["label"] or row["final"] != expected[key]["final"]:
            raise ValueError(f"Sample metadata differs from the fixed manifest: {key}.")
        for name in ARMS:
            arm = row[name]
            if not isinstance(arm, dict) or (
                arm.get("error") is not None and not isinstance(arm["error"], str)
            ):
                raise ValueError(f"Invalid {name} result for {key}.")
            if successful(arm):
                if (
                    not math.isfinite(arm["ms"]) or arm["ms"] < 0
                    or type(arm["bytes"]) is not int or arm["bytes"] <= 0
                    or len(arm["top"]) != 5
                ):
                    raise ValueError(f"Invalid {name} measurement for {key}.")
                for item in arm["top"]:
                    if not isinstance(item["label"], str) or not 0 <= item["index"] < 345:
                        raise ValueError(f"Invalid {name} prediction for {key}.")
        measured[key] = row

    return [
        measured.get(key, {**metadata, "vector": None, "png": None})
        for key, metadata in expected.items()
    ]


def correct(row, arm, top_k):
    return any(item["label"] == row["label"] for item in row[arm]["top"][:top_k])


def accuracy(count, size):
    return 100 * count / size if size else None


def summarize(rows):
    paired = [row for row in rows if all(successful(row[name]) for name in ARMS)]
    final = [row for row in paired if row["final"]]
    summary = {
        "drawings": sum(row["final"] for row in rows),
        "scored_drawings": len(final),
        "strokes": len(paired),
    }
    hits = {name: {k: [correct(row, name, k) for row in final] for k in (1, 5)} for name in ARMS}
    for name in ARMS:
        durations = [row[name]["ms"] for row in paired]
        sizes = [row[name]["bytes"] for row in paired]
        summary[name] = {
            "top1": accuracy(sum(hits[name][1]), len(final)),
            "top5": accuracy(sum(hits[name][5]), len(final)),
            "p50_ms": float(np.percentile(durations, 50)) if durations else None,
            "p95_ms": float(np.percentile(durations, 95)) if durations else None,
            "total_bytes": sum(sizes),
            "mean_bytes": sum(sizes) / len(sizes) if sizes else None,
            "unmapped_top1": sum(row[name]["top"][0]["index"] >= len(model_labels) for row in final),
            "unmapped_top5": sum(
                any(item["index"] >= len(model_labels) for item in row[name]["top"]) for row in final
            ),
        }
    for k in (1, 5):
        pairs = list(zip(hits["vector"][k], hits["png"][k]))
        vector_only = sum(vector and not png for vector, png in pairs)
        png_only = sum(png and not vector for vector, png in pairs)
        summary[f"top{k}_only"] = {"vector": vector_only, "png": png_only}
        summary[f"top{k}_delta_pp"] = accuracy(vector_only - png_only, len(final))
    return summary


def create_report(dataset, submission):
    expected = expected_rows(dataset)
    rows = evaluated_rows(expected, submission["rows"])
    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)
    examples = submission["examples"]
    warmup = submission["warmup_failures"]
    missing = sum(row["vector"] is None for row in rows)
    request_errors = [
        f"{row['id']} · 획 {row['stroke']} · {name}: {row[name]['error']}"
        for row in rows for name in ARMS
        if row[name] is not None and row[name].get("error")
    ]
    preview_errors = [
        f"{example['id']} · 입력 이미지 · {name}: {example[name].get('error') or '이미지 누락'}"
        for example in examples for name in ARMS
        if not example[name].get("image") or example[name].get("error")
    ]
    details = warmup + request_errors + preview_errors
    if missing:
        details.insert(0, f"측정 결과에서 {missing}개의 획이 누락되었습니다.")

    overall = summarize(rows)
    now = datetime.now(timezone.utc)
    run_id = f"{now:%Y%m%dT%H%M%S%f}-{uuid4().hex[:8]}"
    report = {
        "run_id": run_id,
        "status": "partial" if details else "complete",
        "created_at": now.isoformat(),
        "browser": submission["browser"],
        "csv_url": f"/api/results/{run_id}/results.csv",
        "dataset": {key: dataset[key] for key in ("seed", "source", "categories")},
        "completed_drawings": overall["scored_drawings"],
        "expected_drawings": len(dataset["samples"]),
        "paired_strokes": overall["strokes"],
        "expected_strokes": len(expected),
        "failures": {
            "requests": len(request_errors), "missing": missing, "warmup": len(warmup),
            "previews": len(preview_errors), "details": details[:40],
        },
        "overall": overall,
        "by_class": [{"label": name, **summarize(by_label[name])} for name in dataset["categories"]],
        "examples": examples,
    }
    return report, rows


def export_row(row):
    result = {key: row[key] for key in ("id", "label", "stroke", "final")}
    for name in ARMS:
        arm = row[name] or {}
        for key in ("ms", "bytes", "preprocess_ms", "inference_ms"):
            result[f"{name}_{key}"] = arm.get(key)
        result[f"{name}_error"] = "missing" if row[name] is None else arm.get("error")
        for rank in range(1, 6):
            top = arm.get("top", [])
            prediction = top[rank - 1] if rank <= len(top) else {}
            for key in ("index", "label", "probability"):
                result[f"{name}_top{rank}_{key}"] = prediction.get(key)
        for k in (1, 5):
            result[f"{name}_top{k}_correct"] = correct(row, name, k) if successful(row[name]) else None
    return result


def save_report(runs_dir, report, rows):
    run_dir = runs_dir / report["run_id"]
    run_dir.mkdir(parents=True)
    with (run_dir / "results.csv").open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(export_row(rows[0])))
        writer.writeheader()
        writer.writerows(map(export_row, rows))
    temporary = run_dir / "report.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(run_dir / "report.json")


def create_app(dataset, model, runs_dir):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

    @app.get("/")
    def home():
        return render_template("benchmark.html")

    @app.get("/api/dataset")
    def dataset_manifest():
        return jsonify(dataset)

    @app.post("/api/infer/<method>")
    def infer(method):
        if method not in ARMS:
            abort(404)
        request.max_content_length = 1024 * 1024
        start = perf_counter()
        try:
            if method == "vector":
                data = request.get_json(silent=True)
                pixels = vector_input(data.get("strokes") if isinstance(data, dict) else None)
            else:
                pixels = png_input(request.get_data())
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            return jsonify(error=str(error)), 400
        preprocessed = perf_counter()
        top = predict_top_five(model, pixels)
        response = {
            "top": top,
            "preprocess_ms": 1000 * (preprocessed - start),
            "inference_ms": 1000 * (perf_counter() - preprocessed),
        }
        if request.args.get("preview") == "1":
            response["image"] = input_preview(pixels)
        return jsonify(response)

    @app.post("/api/results")
    def results():
        try:
            report, rows = create_report(dataset, request.get_json())
        except (KeyError, IndexError, TypeError, ValueError) as error:
            return jsonify(error=f"Invalid benchmark results: {error}"), 400
        save_report(runs_dir, report, rows)
        return jsonify(report), 201

    @app.get("/api/results/latest")
    def latest():
        saved = max(runs_dir.glob("*/report.json"), default=None)
        if saved is None:
            abort(404)
        response = jsonify(json.loads(saved.read_text(encoding="utf-8")))
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/results/<run_id>/results.csv")
    def csv_download(run_id):
        if not re.fullmatch(r"[0-9]{8}T[0-9]{12}-[0-9a-f]{8}", run_id):
            abort(404)
        run_dir = runs_dir / run_id
        return send_from_directory(run_dir, "results.csv", as_attachment=True)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=WORK_DIR / "dataset.json")
    parser.add_argument("--runs-dir", type=Path, default=WORK_DIR / "runs")
    args = parser.parse_args()
    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.error(f"Cannot read {args.dataset}. Prepare it with benchmark_data.py. {error}")
    if not dataset.get("samples"):
        parser.error("The benchmark manifest contains no samples.")
    torch.set_num_threads(4)
    model = load_model()
    app = create_app(dataset, model, args.runs_dir.resolve())
    app.run(host="127.0.0.1", port=5001, threaded=False)


if __name__ == "__main__":
    main()

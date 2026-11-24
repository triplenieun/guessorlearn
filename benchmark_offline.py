"""Evaluate the model directly on the benchmark's complete Quick, Draw! strokes."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from benchmark_data import DATASET_PATH
from model_inference import label as model_labels
from model_inference import load_model
from vector_to_image import transformer_vec_img


COORDINATE_SIZE = 256
DRAWING_SIZE = 240
BATCH_SIZE = 32
CPU_THREADS = 4


def drawing_input(strokes):
    if not strokes or any(not xs or len(xs) != len(ys) for xs, ys in strokes):
        raise ValueError("Expected nonempty strokes with matching x and y coordinates.")

    x_axes, y_axes = zip(*strokes)
    min_x, max_x = min(map(min, x_axes)), max(map(max, x_axes))
    min_y, max_y = min(map(min, y_axes)), max(map(max, y_axes))
    width, height = max_x - min_x, max_y - min_y
    scale = DRAWING_SIZE / (max(width, height) or 1)
    left = (COORDINATE_SIZE - width * scale) / 2
    top = (COORDINATE_SIZE - height * scale) / 2
    centered = [
        [
            [int(left + (x - min_x) * scale) for x in xs],
            [int(top + (y - min_y) * scale) for y in ys],
        ]
        for xs, ys in strokes
    ]
    return transformer_vec_img(centered)


def load_inputs(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    samples = manifest.get("samples") if isinstance(manifest, dict) else None
    if not isinstance(samples, list) or not samples:
        raise ValueError("Expected a nonempty 'samples' list.")

    label_indices = {name: index for index, name in enumerate(model_labels)}
    images, targets = [], []
    for number, sample in enumerate(samples, start=1):
        try:
            images.append(drawing_input(sample["strokes"]))
            targets.append(label_indices[sample["label"]])
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid sample {number}: {error}") from error
    return torch.from_numpy(np.concatenate(images)), torch.tensor(targets)


def evaluate(model, images, targets):
    top1_correct = top5_correct = 0
    with torch.inference_mode():
        for start in range(0, len(targets), BATCH_SIZE):
            end = start + BATCH_SIZE
            # Rank every output, including indices outside the app's label mapping.
            top5 = model(images[start:end].float()).topk(5, dim=1).indices
            matches = top5 == targets[start:end, None]
            top1_correct += int(matches[:, 0].sum())
            top5_correct += int(matches.any(dim=1).sum())
    return top1_correct, top5_correct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    args = parser.parse_args()
    try:
        images, targets = load_inputs(args.dataset)
    except OSError as error:
        parser.error(f"Cannot read {args.dataset}. Run benchmark_data.py first. {error}")
    except ValueError as error:
        parser.error(f"Invalid dataset manifest {args.dataset}. {error}")

    torch.set_num_threads(CPU_THREADS)
    top1, top5 = evaluate(load_model(), images, targets)
    total = len(targets)
    print(f"Evaluated {total} drawings")
    print(f"Top-1 {top1}/{total} ({100 * top1 / total:.2f}%)")
    print(f"Top-5 {top5}/{total} ({100 * top5 / total:.2f}%)")


if __name__ == "__main__":
    main()

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "project_env" / "benchmark" / "dataset.json"
SOURCE = "https://github.com/googlecreativelab/quickdraw-dataset"
CATEGORIES_URL = (
    "https://raw.githubusercontent.com/googlecreativelab/quickdraw-dataset/"
    "master/categories.txt"
)
RAW_URL = "https://storage.googleapis.com/quickdraw_dataset/full/raw"
SEED = "guessorlearn-benchmark-v1"
CLASS_COUNT = 32
SAMPLES_PER_CLASS = 20
SUFFIX_BYTES = 4 * 1024 * 1024


def model_labels():
    # Read the app's label mapping without importing PyTorch into the downloader.
    source = (ROOT / "model_inference.py").read_text(encoding="utf-8")
    for assignment in ast.parse(source).body:
        if isinstance(assignment, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "label"
            for target in assignment.targets
        ):
            return ast.literal_eval(assignment.value)
    raise ValueError("No label mapping found in model_inference.py")


def stable_order(scope, value):
    return hashlib.sha256(f"{SEED}\0{scope}\0{value}".encode("utf-8")).digest()


def download(url, limit, range_header=None):
    headers = {"Accept-Encoding": "identity"}
    if range_header is not None:
        headers["Range"] = range_header
    request = Request(url, headers=headers)

    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                start = 0
                if range_header is not None:
                    content_range = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
                    if response.status != 206 or match is None:
                        raise ValueError(f"Expected a partial response for {url}")
                    start, end, total = (int(value) for value in match.groups())
                    if start != max(0, total - limit) or end != total - 1:
                        raise ValueError(f"Unexpected Content-Range for {url}: {content_range}")
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError(f"Response exceeded {limit} bytes for {url}")
                if range_header is not None and len(body) != end - start + 1:
                    raise ConnectionError(f"Incomplete range downloaded from {url}")
                return body, start
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def valid_strokes(drawing):
    if not isinstance(drawing, list) or not drawing:
        return None

    strokes = []
    has_line = False
    for stroke in drawing:
        if not isinstance(stroke, list) or len(stroke) != 3:
            return None
        x_values, y_values, times = stroke
        if not all(isinstance(axis, list) for axis in stroke):
            return None
        if not x_values or len(x_values) != len(y_values) or len(x_values) != len(times):
            return None
        if not all(type(t) is int and t >= 0 for t in times):
            return None
        if not all(
            type(value) in (int, float) and math.isfinite(value)
            for axis in (x_values, y_values)
            for value in axis
        ):
            return None
        has_line |= min(x_values) != max(x_values) or min(y_values) != max(y_values)
        strokes.append([x_values, y_values])
    return strokes if has_line else None


def valid_samples(lines, category):
    seen = set()
    for line in lines:
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(record, dict) or record.get("word") != category:
            continue
        if record.get("recognized") is not True:
            continue
        sample_id = str(record.get("key_id", ""))
        if not sample_id.isascii() or not sample_id.isdecimal() or sample_id in seen:
            continue
        strokes = valid_strokes(record.get("drawing"))
        if strokes is None:
            continue
        seen.add(sample_id)
        yield {"id": sample_id, "label": category, "strokes": strokes}


def samples_from_category(category):
    url = f"{RAW_URL}/{quote(category, safe='')}.ndjson"
    body, start = download(url, SUFFIX_BYTES, range_header=f"bytes=-{SUFFIX_BYTES}")
    lines = iter(body.splitlines())
    if start:
        # A suffix can begin in the middle of a JSON record.
        next(lines, None)
    samples = heapq.nsmallest(
        SAMPLES_PER_CLASS,
        valid_samples(lines, category),
        key=lambda record: stable_order(category, record["id"]),
    )
    if len(samples) != SAMPLES_PER_CLASS:
        raise ValueError(f"{category}: found only {len(samples)} valid drawings in the range")
    return samples


def build_dataset():
    category_list, _ = download(CATEGORIES_URL, 32 * 1024)
    eligible = set(model_labels()).intersection(category_list.decode("utf-8").splitlines())
    categories = sorted(eligible, key=lambda name: stable_order("category", name))[:CLASS_COUNT]
    if len(categories) != CLASS_COUNT:
        raise ValueError(f"Found only {len(categories)} model labels in the official category list")

    samples = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for category, examples in zip(categories, executor.map(samples_from_category, categories)):
            samples.extend(examples)
            print(f"{category}: {len(examples)} drawings", flush=True)

    if len({record["id"] for record in samples}) != len(samples):
        raise ValueError("Selected Quick, Draw! IDs are not globally unique")
    samples.sort(key=lambda record: stable_order("replay", record["id"]))
    return {"seed": SEED, "source": SOURCE, "categories": categories, "samples": samples}


def write_dataset(dataset, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as file:
            temp_path = Path(file.name)
            json.dump(dataset, file, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            file.write("\n")
        temp_path.replace(destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Prepare the fixed Quick, Draw! benchmark sample.")
    parser.add_argument("--output", type=Path, default=DATASET_PATH)
    args = parser.parse_args()
    try:
        dataset = build_dataset()
        write_dataset(dataset, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not prepare the benchmark dataset: {error}\n")
    print(f"Saved {len(dataset['samples'])} drawings to {args.output.resolve()}")


if __name__ == "__main__":
    main()

const CANVAS_SIZE = 512;
const DRAWING_SIZE = 480;
const WARMUP_PAIRS = 10;
const REQUEST_TIMEOUT_MS = 30_000;
const USED_COLORS = Array(10).fill(0);

function fitDrawing(strokes) {
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const [xs, ys] of strokes) {
        for (let i = 0; i < xs.length; i++) {
            minX = Math.min(minX, xs[i]);
            maxX = Math.max(maxX, xs[i]);
            minY = Math.min(minY, ys[i]);
            maxY = Math.max(maxY, ys[i]);
        }
    }

    const width = maxX - minX;
    const height = maxY - minY;
    const scale = DRAWING_SIZE / (Math.max(width, height) || 1);
    const left = (CANVAS_SIZE - width * scale) / 2;
    const top = (CANVAS_SIZE - height * scale) / 2;
    return strokes.map(([xs, ys]) => [
        xs.map(x => left + (x - minX) * scale),
        ys.map(y => top + (y - minY) * scale),
    ]);
}

function resetCanvas(ctx) {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    ctx.strokeStyle = 'black';
    ctx.lineWidth = 3;
    ctx.lineCap = 'butt';
    ctx.imageSmoothingEnabled = false;
}

function replayStroke(ctx, [xs, ys]) {
    // Each pointer move in the app paints its segment separately.
    ctx.beginPath();
    ctx.moveTo(xs[0], ys[0]);
    const recordedX = [Math.trunc(xs[0])];
    const recordedY = [Math.trunc(ys[0])];
    for (let i = 1; i < xs.length; i++) {
        ctx.lineTo(xs[i], ys[i]);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(xs[i], ys[i]);

        // Match newstroke.js: both coordinates must change from the last recorded point.
        const x = Math.trunc(xs[i]);
        const y = Math.trunc(ys[i]);
        if (x !== recordedX.at(-1) && y !== recordedY.at(-1)) {
            recordedX.push(x);
            recordedY.push(y);
        }
    }
    return [recordedX, recordedY];
}

function encodePng(canvas) {
    return new Promise((resolve, reject) => {
        canvas.toBlob(blob => {
            if (blob) {
                resolve(blob);
            } else {
                reject(new Error('Could not encode canvas PNG'));
            }
        }, 'image/png');
    });
}

async function infer(method, canvas, strokes, preview) {
    const start = performance.now();
    let bytes = 0;
    try {
        const body = method === 'vector'
            ? new Blob([JSON.stringify({strokes, used_color_list: USED_COLORS})], {type: 'application/json'})
            : await encodePng(canvas);
        bytes = body.size;
        const url = `/api/infer/${method}${preview ? '?preview=1' : ''}`;
        const response = await fetch(url, {
            method: 'POST',
            body,
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        const result = await response.json();
        const ms = performance.now() - start;
        if (!response.ok || result.error) {
            throw new Error(result.error || `HTTP ${response.status}`);
        }
        if (result.top?.length !== 5 || !Number.isFinite(result.preprocess_ms)
            || !Number.isFinite(result.inference_ms) || (preview && !result.image)) {
            throw new Error('Incomplete inference response');
        }
        return {...result, ms, bytes};
    } catch (error) {
        return {
            ms: performance.now() - start,
            bytes,
            top: [],
            preprocess_ms: null,
            inference_ms: null,
            error: error.message,
        };
    }
}

async function inferPair(canvas, strokes, pairIndex, preview = false) {
    const order = pairIndex % 2 === 0 ? ['vector', 'png'] : ['png', 'vector'];
    const pair = {};
    for (const method of order) {
        pair[method] = await infer(method, canvas, strokes, preview);
    }
    return pair;
}

function top1Outcome(row) {
    const vectorCorrect = row.vector.top[0].label === row.label;
    const pngCorrect = row.png.top[0].label === row.label;
    if (vectorCorrect && pngCorrect) return 'both_right';
    if (vectorCorrect) return 'vector_only';
    if (pngCorrect) return 'png_only';
    return 'both_wrong';
}

export async function runBenchmark(dataset, {onProgress = () => {}} = {}) {
    const canvas = document.createElement('canvas');
    canvas.width = CANVAS_SIZE;
    canvas.height = CANVAS_SIZE;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D is unavailable');

    const {samples} = dataset;
    const warmup = samples.slice(0, WARMUP_PAIRS);
    const warmupFailures = [];
    let pairIndex = 0;

    onProgress({stage: 'warmup', complete: 0, total: warmup.length});
    for (const sample of warmup) {
        resetCanvas(ctx);
        const [first] = fitDrawing(sample.strokes);
        const pair = await inferPair(canvas, [replayStroke(ctx, first)], pairIndex++);
        for (const [method, result] of Object.entries(pair)) {
            if (result.error) warmupFailures.push(`${sample.id} (${method}): ${result.error}`);
        }
        onProgress({stage: 'warmup', complete: pairIndex, total: warmup.length});
    }

    const rows = [];
    const previewSamples = new Map();
    onProgress({stage: 'measure', complete: 0, total: samples.length});
    for (const [sampleIndex, sample] of samples.entries()) {
        resetCanvas(ctx);
        const drawing = fitDrawing(sample.strokes);
        const strokes = [];
        for (const [strokeIndex, stroke] of drawing.entries()) {
            strokes.push(replayStroke(ctx, stroke));
            const pair = await inferPair(canvas, strokes, pairIndex++);
            const final = strokeIndex === drawing.length - 1;
            const row = {id: sample.id, label: sample.label, stroke: strokeIndex + 1, final, ...pair};
            rows.push(row);
            if (final && !row.vector.error && !row.png.error) {
                const outcome = top1Outcome(row);
                if (!previewSamples.has(outcome)) previewSamples.set(outcome, sample);
            }
        }
        onProgress({stage: 'measure', complete: sampleIndex + 1, total: samples.length});
    }

    const examples = [];
    onProgress({stage: 'preview', complete: 0, total: previewSamples.size});
    for (const [outcome, sample] of previewSamples) {
        resetCanvas(ctx);
        const strokes = fitDrawing(sample.strokes).map(stroke => replayStroke(ctx, stroke));
        const pair = await inferPair(canvas, strokes, pairIndex++, true);
        examples.push({id: sample.id, label: sample.label, outcome, ...pair});
        onProgress({stage: 'preview', complete: examples.length, total: previewSamples.size});
    }

    onProgress({stage: 'done', complete: samples.length, total: samples.length});
    return {rows, examples, browser: navigator.userAgent, warmup_failures: warmupFailures};
}

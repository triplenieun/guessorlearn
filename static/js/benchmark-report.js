import { runBenchmark } from './benchmark-runner.js';

const runButton = document.getElementById('run');
const statusLine = document.getElementById('status');
const progress = document.getElementById('progress');
const alertBox = document.getElementById('run-error');
const reportPanel = document.getElementById('report');
const download = document.getElementById('download');
const exampleChoice = document.getElementById('example-choice');
const classMetric = document.getElementById('class-metric');

const methodLabels = { png: 'Canvas PNG', vector: '현재 벡터' };
const methods = ['png', 'vector'];
const outcomes = {
    vector_only: '벡터만 1위 정답',
    png_only: 'PNG만 1위 정답',
    both_right: '두 방식 모두 1위 정답',
    both_wrong: '두 방식 모두 1위 오답',
};
const outcomePriority = Object.keys(outcomes);

const integerFormat = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 });
const decimalFormat = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });
const dateFormat = new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
let currentReport;

function element(tag, content, className) {
    const node = document.createElement(tag);
    if (content != null) node.textContent = content;
    if (className) node.className = className;
    return node;
}

function formatInteger(value) {
    return Number.isFinite(value) ? integerFormat.format(value) : '—';
}

function formatDecimal(value, unit = '') {
    return Number.isFinite(value) ? `${decimalFormat.format(value)}${unit}` : '—';
}

function formatDelta(value) {
    if (!Number.isFinite(value)) return '—';
    return `${value > 0 ? '+' : ''}${formatDecimal(value, '%p')}`;
}

async function fetchJson(path, options) {
    const response = await fetch(path, { cache: 'no-store', ...options });
    const body = await response.json().catch(() => null);
    if (!response.ok || body === null) {
        const error = new Error(body?.error || body?.message || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return body;
}

function accuracyCard(heading, metric, results) {
    const card = metricCard(heading, method => formatDecimal(results[method]?.[metric], '%'));
    const only = results[`${metric}_only`];
    card.append(
        element('p', `벡터 − PNG ${formatDelta(results[`${metric}_delta_pp`])}`, 'delta'),
        element('p', `PNG만 ${formatInteger(only?.png)}장 · 벡터만 ${formatInteger(only?.vector)}장`, 'pair-count'),
    );
    return card;
}

function metricCard(heading, getValue, note) {
    const card = element('article', null, 'metric');
    card.append(element('h3', heading));
    const values = element('dl');
    for (const method of methods) {
        const row = element('div');
        row.append(element('dt', methodLabels[method], `arm-${method}`), element('dd', getValue(method)));
        values.append(row);
    }
    card.append(values);
    if (note) card.append(element('p', note, 'measure-note'));
    return card;
}

function renderMetrics(report) {
    const results = report.overall;
    const responseTimes = metricCard('획당 응답 시간', method => {
        const arm = results[method];
        return `${formatDecimal(arm?.p50_ms)} / ${formatDecimal(arm?.p95_ms, ' ms')}`;
    }, 'p50 / p95');
    const requestSize = metricCard('요청 본문 크기', method => {
        const arm = results[method];
        return `${formatInteger(arm?.mean_bytes)} / ${formatInteger(arm?.total_bytes)} B`;
    }, '획당 평균 / 전체 합계');
    document.getElementById('metrics').replaceChildren(
        accuracyCard('Top-1 정확도', 'top1', results),
        accuracyCard('Top-5 정확도', 'top5', results),
        responseTimes,
        requestSize,
    );
    const unmapped = document.getElementById('unmapped-summary');
    unmapped.hidden = !methods.some(method => results[method]?.unmapped_top5 > 0);
    if (!unmapped.hidden) {
        const counts = methods.map(method => {
            const arm = results[method];
            return `${methodLabels[method]} ${formatInteger(arm.unmapped_top1)}장 / ${formatInteger(arm.unmapped_top5)}장`;
        });
        unmapped.textContent = `미등록 출력이 포함된 완성 그림 (Top-1 / Top-5) · ${counts.join(' · ')}`;
    }
}

function renderFailures(report) {
    const { requests, missing, warmup, previews, details } = report.failures;
    const failureBox = document.getElementById('failures');
    const detailBox = document.getElementById('failure-details');
    const detailsList = document.getElementById('failure-list');
    const counts = [
        ['측정 요청 실패', requests], ['누락 획', missing], ['워밍업 오류', warmup], ['미리보기 오류', previews],
    ];
    const issues = counts.filter(([, count]) => count > 0).map(([name, count]) => `${name} ${formatInteger(count)}건`);
    failureBox.hidden = issues.length === 0 && report.status !== 'partial';
    document.getElementById('failure-summary').textContent = issues.length
        ? issues.join(' · ')
        : '일부 그림의 결과가 완성되지 않았습니다.';
    detailsList.replaceChildren(...details.map(detail => element('li', detail)));
    detailBox.hidden = details.length === 0;
    detailBox.open = false;
}

function previewCard(example, method) {
    const title = methodLabels[method];
    const arm = example[method];
    const card = element('article', null, `preview arm-${method}`);
    card.append(element('h3', title));
    if (!arm?.image || arm.error) {
        card.append(element('p', arm?.error ?? '모델 입력을 불러오지 못했습니다.', 'preview-error'));
        return card;
    }

    const body = element('div', null, 'preview-body');
    const image = element('img');
    image.src = arm.image;
    image.width = 64;
    image.height = 64;
    image.alt = `${title} 64×64 모델 입력 · ${example.label}`;

    const predictions = element('ol');
    predictions.setAttribute('aria-label', `${title}의 예측 순위`);
    for (const prediction of arm.top) {
        const item = element('li');
        const correct = prediction.label === example.label;
        const rank = element('div', null, correct ? 'rank rank--correct' : 'rank');
        const text = prediction.index >= 328 || !prediction.label
            ? `미등록 #${prediction.index}` : prediction.label;
        const name = element('span', text);
        if (correct) name.append(element('span', ' (정답)', 'sr-only'));
        rank.append(name, element('span', formatDecimal(prediction.probability * 100, '%'), 'rank-value'));
        item.append(rank);
        predictions.append(item);
    }
    body.append(image, predictions);
    card.append(body);
    return card;
}

function renderExample(example) {
    const container = document.getElementById('examples');
    if (!example) {
        container.replaceChildren(element('p', '표시할 모델 입력이 없습니다.'));
        return;
    }
    const meta = element('p', null, 'figure-meta');
    meta.append(
        element('strong', `정답 ${example.label}`),
        element('small', `표본 ${example.id}`),
    );
    const grid = element('div', null, 'figure-grid');
    grid.append(...methods.map(method => previewCard(example, method)));
    container.replaceChildren(meta, grid);
}

function renderExamples(examples) {
    const control = document.getElementById('example-control');
    const indexes = examples.map((_, index) => index);
    indexes.sort((left, right) => (
        examplePriority(examples[left].outcome) - examplePriority(examples[right].outcome)
    ));
    exampleChoice.replaceChildren(...indexes.map(index => {
        const example = examples[index];
        const description = outcomes[example.outcome] ?? '모델 입력 비교';
        const option = element('option', `${description} · ${example.label}`);
        option.value = index;
        return option;
    }));
    control.hidden = examples.length === 0;
    renderExample(examples[indexes[0]]);
}

function examplePriority(outcome) {
    const position = outcomePriority.indexOf(outcome);
    return position === -1 ? outcomePriority.length : position;
}

function classColumns(metric) {
    const png = 'Canvas PNG';
    const vector = '현재 벡터';
    if (metric === 'latency') {
        return [
            ['획 쌍', row => formatInteger(row.strokes)],
            [`${png} p50 (ms)`, row => formatDecimal(row.png?.p50_ms)],
            [`${vector} p50 (ms)`, row => formatDecimal(row.vector?.p50_ms)],
            [`${png} p95 (ms)`, row => formatDecimal(row.png?.p95_ms)],
            [`${vector} p95 (ms)`, row => formatDecimal(row.vector?.p95_ms)],
        ];
    }
    if (metric === 'bytes') {
        return [
            ['획 쌍', row => formatInteger(row.strokes)],
            [`${png} 합계 (B)`, row => formatInteger(row.png?.total_bytes)],
            [`${vector} 합계 (B)`, row => formatInteger(row.vector?.total_bytes)],
            [`${png} 평균 (B)`, row => formatDecimal(row.png?.mean_bytes)],
            [`${vector} 평균 (B)`, row => formatDecimal(row.vector?.mean_bytes)],
        ];
    }
    return [
        ['그림 (평가/대상)', row => `${formatInteger(row.scored_drawings)} / ${formatInteger(row.drawings)}`],
        [png, row => formatDecimal(row.png?.[metric], '%')],
        [vector, row => formatDecimal(row.vector?.[metric], '%')],
        ['벡터 − PNG', row => formatDelta(row[`${metric}_delta_pp`])],
        ['PNG만 정답', row => formatInteger(row[`${metric}_only`]?.png)],
        ['벡터만 정답', row => formatInteger(row[`${metric}_only`]?.vector)],
    ];
}

function renderClasses(classes) {
    const table = document.getElementById('class-table');
    const columns = classColumns(classMetric.value);
    const metricLabel = classMetric.selectedOptions[0].textContent;
    const caption = element('caption', `클래스별 ${metricLabel}`, 'sr-only');
    const head = element('thead');
    const headings = element('tr');
    for (const name of ['클래스', ...columns.map(([heading]) => heading)]) {
        const header = element('th', name);
        header.scope = 'col';
        headings.append(header);
    }
    head.append(headings);
    const body = element('tbody');
    for (const data of [...classes].sort((left, right) => left.label.localeCompare(right.label, 'en'))) {
        const row = element('tr');
        const name = element('th', data.label);
        name.scope = 'row';
        row.append(name, ...columns.map(([, getValue]) => element('td', getValue(data))));
        body.append(row);
    }
    table.replaceChildren(caption, head, body);
}

function renderReport(report) {
    currentReport = report;
    renderMetrics(report);
    renderFailures(report);
    renderExamples(report.examples);
    renderClasses(report.by_class);
    document.getElementById('coverage').textContent =
        `완성 그림 ${formatInteger(report.completed_drawings)}/${formatInteger(report.expected_drawings)}장 · ` +
        `획 ${formatInteger(report.paired_strokes)}/${formatInteger(report.expected_strokes)}쌍`;
    const timestamp = new Date(report.created_at);
    const metadata = document.getElementById('metadata');
    metadata.textContent = `표본 시드 ${report.dataset.seed} · 브라우저 ${report.browser}`;
    metadata.hidden = false;
    const state = report.status === 'complete' ? '측정 완료' : '일부 결과 저장됨';
    statusLine.textContent = Number.isFinite(timestamp.valueOf()) ? `${state} · ${dateFormat.format(timestamp)}` : state;
    download.href = report.csv_url;
    download.hidden = false;
    runButton.textContent = '다시 실행';
    reportPanel.hidden = false;
}

function showProgress({ stage, complete, total }) {
    progress.hidden = false;
    if (total > 0) {
        progress.max = total;
        progress.value = complete;
    } else {
        progress.removeAttribute('value');
    }
    if (stage === 'measure' && complete > 0 && complete < total && complete % 10 !== 0) return;
    const phase = { warmup: '워밍업', measure: '그림 재생 및 측정', preview: '모델 입력 미리보기', done: '측정 결과 저장 중' }[stage];
    if (phase) statusLine.textContent = total > 0 && stage !== 'done' ? `${phase} ${complete}/${total}` : phase;
}

async function restoreReport() {
    try {
        renderReport(await fetchJson('/api/results/latest'));
    } catch (error) {
        statusLine.textContent = '벤치마크를 실행하면 이곳에 결과가 표시됩니다.';
        if (error.status !== 404) {
            alertBox.textContent = `저장된 결과를 불러오지 못했습니다. ${error.message}`;
            alertBox.hidden = false;
        }
    } finally {
        runButton.disabled = false;
    }
}

async function execute() {
    runButton.disabled = true;
    alertBox.hidden = true;
    progress.hidden = false;
    progress.removeAttribute('value');
    statusLine.textContent = '고정 표본을 불러오는 중입니다.';
    try {
        const dataset = await fetchJson('/api/dataset');
        const measured = await runBenchmark(dataset, { onProgress: showProgress });
        const saved = await fetchJson('/api/results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(measured),
        });
        renderReport(saved);
    } catch (error) {
        statusLine.textContent = currentReport ? '마지막으로 저장한 결과를 표시합니다.' : '측정이 중단되었습니다.';
        alertBox.textContent = `벤치마크 오류. ${error.message}`;
        alertBox.hidden = false;
    } finally {
        runButton.disabled = false;
        progress.hidden = true;
    }
}

runButton.addEventListener('click', execute);
exampleChoice.addEventListener('change', () => renderExample(currentReport.examples[Number(exampleChoice.value)]));
classMetric.addEventListener('change', () => renderClasses(currentReport.by_class));
restoreReport();

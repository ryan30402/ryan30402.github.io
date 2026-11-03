/* Read-only browser explorer for the supplied Linear Perf Lab v0.4 results. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  if (!byId('perf-model-bars')) return;
  const controls = ['perf-dtype', 'perf-round', 'perf-split', 'perf-metric'];
  const fmt = value => Number(value).toFixed(2);
  const metricNames = { median_ape_pct: 'median APE', p90_ape_pct: 'P90 APE' };
  const splitNames = { development: 'Development', test: 'Test', challenge: 'Challenge' };
  const make = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  let data;
  let names;
  let shapes;

  function renderModels() {
    const dtype = byId('perf-dtype').value;
    const round = byId('perf-round').value;
    const split = byId('perf-split').value;
    const metric = byId('perf-metric').value;
    const session = `${dtype}_${round}`;
    const rows = data.models.map(model => data.metrics.find(row =>
      row.session_id === session && row.split === split && row.model_id === model.id));
    if (rows.some(row => !row)) throw new Error('Incomplete model result group.');
    const selected = rows.find(row => row.selected_by_development);
    if (!selected) throw new Error('No recorded development selection.');
    const max = Math.ceil(Math.max(...rows.map(row => row[metric])) / 10) * 10 || 1;
    const root = byId('perf-model-bars');
    root.replaceChildren();
    for (const row of rows) {
      const item = make('div', 'lp-model-row');
      item.dataset.model = row.model_id;
      item.dataset.value = String(row[metric]);
      const label = make('div', 'lp-bar-label');
      const name = make('span', 'lp-model-name', names[row.model_id]);
      if (row.selected_by_development) name.append(make('span', 'lp-selected-label', 'Selected'));
      label.append(name, make('strong', null, `${fmt(row[metric])}%`));
      const track = make('div', 'lp-track');
      track.setAttribute('aria-hidden', 'true');
      const bar = make('i', `lp-bar${row.selected_by_development ? ' selected' : ''}`);
      bar.style.width = `${100 * row[metric] / max}%`;
      track.append(bar);
      item.append(label, track);
      root.append(item);
    }
    const lowest = rows.reduce((best, row) => row[metric] < best[metric] ? row : best);
    byId('perf-chart-caption').textContent = `${session} · ${splitNames[split]} · ${rows[0].n_shapes} shapes · axis 0–${max}%`;
    byId('perf-selected-model').textContent = names[selected.model_id];
    byId('perf-selected-error').textContent = `${fmt(selected[metric])}%`;
    byId('perf-selected-context').textContent = `${splitNames[split]} ${metricNames[metric]} for the originally selected model.`;
    const same = lowest.model_id === selected.model_id;
    byId('perf-comparison-note').textContent = same
      ? `This selected model also has the lowest ${metricNames[metric]} in this view. Selection still used development data only.`
      : `${names[lowest.model_id]} has the lowest displayed ${metricNames[metric]} (${fmt(lowest[metric])}%). That does not change the recorded selection.`;
    byId('perf-live-status').textContent = `${dtype.toUpperCase()}, round ${round.slice(1)}, ${split}: selected ${names[selected.model_id]}, ${metricNames[metric]} ${fmt(selected[metric])}%.`;
  }

  function renderShape() {
    const id = byId('perf-shape').value;
    const rows = data.paired_latencies.filter(row => row.case_id === id).sort((a, b) => a.round.localeCompare(b.round));
    if (rows.length !== 3) throw new Error('Expected three recorded rounds per shape.');
    const max = Math.max(...rows.flatMap(row => [row.fp16_latency_us, row.bf16_latency_us])) * 1.05;
    const root = byId('perf-latency-bars');
    root.replaceChildren();
    for (const row of rows) {
      const group = make('div', 'lp-latency-group');
      group.append(make('span', 'lp-round-label', `ROUND ${row.round.slice(1)} · ${row.round}`));
      for (const dtype of ['fp16', 'bf16']) {
        const value = row[`${dtype}_latency_us`];
        const line = make('div', 'lp-latency-row');
        line.dataset.round = row.round;
        line.dataset.dtype = dtype;
        line.dataset.value = String(value);
        const track = make('div', 'lp-track');
        track.setAttribute('aria-hidden', 'true');
        const bar = make('i', `lp-bar${dtype === 'fp16' ? ' selected' : ''}`);
        bar.style.width = `${value / max * 100}%`;
        track.append(bar);
        line.append(make('span', null, dtype.toUpperCase()), track, make('b', null, `${fmt(value)} µs`));
        group.append(line);
      }
      root.append(group);
    }
    const first = rows[0];
    byId('perf-shape-id').textContent = `${id} · ${first.split}`;
    for (const dimension of ['m', 'n', 'k']) byId(`perf-${dimension}`).textContent = String(first[dimension]);
    const fpWins = rows.filter(row => row.fp16_latency_us < row.bf16_latency_us).length;
    const bfWins = rows.filter(row => row.bf16_latency_us < row.fp16_latency_us).length;
    byId('perf-shape-status').textContent = `Observed lower latency: FP16 in ${fpWins}/3 rounds; BF16 in ${bfWins}/3 rounds. This is a descriptive comparison, not a significance test.`;
    document.querySelectorAll('[data-example]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.example === id)));
  }

  function validate(input) {
    if (!input || input.schema_version !== 1 || !Array.isArray(input.models) || input.models.length !== 5 || !Array.isArray(input.metrics) || input.metrics.length !== 90 || !Array.isArray(input.paired_latencies) || input.paired_latencies.length !== 288) throw new Error('Unexpected result schema.');
    for (const row of input.metrics) {
      for (const key of ['median_ape_pct', 'p90_ape_pct']) if (!Number.isFinite(row[key]) || row[key] < 0) throw new Error('Invalid error value.');
    }
    for (const row of input.paired_latencies) {
      if (!Number.isFinite(row.fp16_latency_us) || !Number.isFinite(row.bf16_latency_us) || row.fp16_latency_us <= 0 || row.bf16_latency_us <= 0) throw new Error('Invalid latency value.');
    }
    return input;
  }

  function showError(error) {
    console.error('The recorded-results explorer could not load:', error);
    byId('perf-data-error').hidden = false;
    byId('perf-chart-caption').textContent = 'Interactive results unavailable. See the recorded table below.';
    controls.forEach(id => { byId(id).disabled = true; });
    byId('perf-shape').disabled = true;
    document.querySelectorAll('[data-example]').forEach(button => { button.disabled = true; });
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  fetch('/assets/linear-perf/results.json', { signal: controller.signal })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(input => {
      data = validate(input);
      names = Object.fromEntries(data.models.map(model => [model.id, model.label]));
      shapes = data.paired_latencies.filter(row => row.round === 's01').sort((a, b) => a.case_id.localeCompare(b.case_id));
      const select = byId('perf-shape');
      select.replaceChildren();
      for (const row of shapes) {
        const option = make('option', null, `${row.case_id} · ${row.m} × ${row.n} × ${row.k} · ${row.split}`);
        option.value = row.case_id;
        select.append(option);
      }
      select.value = 't22';
      renderModels();
      renderShape();
      controls.forEach(id => {
        byId(id).disabled = false;
        byId(id).addEventListener('change', () => { try { renderModels(); } catch (error) { showError(error); } });
      });
      select.disabled = false;
      select.addEventListener('change', () => { try { renderShape(); } catch (error) { showError(error); } });
      document.querySelectorAll('[data-example]').forEach(button => {
        button.disabled = false;
        button.addEventListener('click', () => {
          select.value = button.dataset.example;
          try { renderShape(); } catch (error) { showError(error); }
        });
      });
    })
    .catch(showError)
    .finally(() => window.clearTimeout(timeout));
})();

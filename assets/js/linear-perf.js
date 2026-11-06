/* Read-only explorer for Transformer Linear Layer Performance Predictor, release 1.1.0. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  if (!byId('perf-model-bars')) return;

  const controls = ['perf-dtype', 'perf-policy', 'perf-split', 'perf-metric'];
  const metricNames = {
    weighted_mean_ape_pct: 'weighted mean APE',
    mean_ape_pct: 'unweighted mean APE',
    median_ape_pct: 'unweighted median APE',
    p90_ape_pct: 'unweighted P90 APE',
    worst_ape_pct: 'unweighted worst-case APE'
  };
  const splitNames = { train: 'Train', test: 'Ordinary test', challenge: 'Family challenge', stress: 'Irregular stress' };
  const shortSplitNames = { train: 'Train', test: 'Test', challenge: 'Challenge', stress: 'Stress' };
  const dtypeNames = { float16: 'FP16', bfloat16: 'BF16' };
  const policyNames = { warm_reuse: 'Warm reuse', rotating_buffers: 'Four-buffer rotation' };
  const scopeNotes = {
    test: 'Ordinary test uses unseen M values in N/K families represented in training.',
    challenge: 'Family challenge holds out complete N/K families from training and model selection.',
    stress: 'Irregular stress changes N and K by +1. These artificial alignment states have no matching training examples.'
  };
  const metricNotes = {
    weighted_mean_ape_pct: 'Weighted mean APE uses declared architectural-operation weights under a synthetic workload mixture. These weights do not represent measured production traffic.',
    mean_ape_pct: 'Unweighted mean APE averages the per-shape percentage errors with equal weight for every case.',
    median_ape_pct: 'Unweighted median APE is the middle per-shape error. Large errors affecting fewer than half the shapes can remain above this value.',
    p90_ape_pct: 'Unweighted P90 APE is the 90th percentile of the per-shape errors, with equal weight for every case.',
    worst_ape_pct: 'Unweighted worst-case APE is the largest per-shape percentage error in this context and evaluation scope.'
  };
  const fmt = value => Number(value).toFixed(2);
  const count = value => Number(value).toLocaleString('en-US');
  const make = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  let data;
  let modelNames;
  let metricIndex;
  let families;

  function contextFor(dtype, policy) {
    const context = data.contexts.find(row => row.dtype === dtype && row.cache_policy === policy);
    if (!context) throw new Error('Missing precision/buffer context.');
    return context;
  }

  function renderModels() {
    const dtype = byId('perf-dtype').value;
    const policy = byId('perf-policy').value;
    const split = byId('perf-split').value;
    const metric = byId('perf-metric').value;
    const context = contextFor(dtype, policy);
    const rows = data.models.map(model => metricIndex.get(`${context.id}|${split}|${model.id}`));
    if (rows.some(row => !row) || !metricNames[metric]) throw new Error('Incomplete model result group.');
    const selected = rows.find(row => row.selected_by_cv);
    if (!selected) throw new Error('Missing training-only model selection.');

    for (const option of byId('perf-split').options) {
      option.textContent = `${splitNames[option.value]} · ${context.split_counts[option.value]} shapes`;
    }
    const max = Math.ceil(Math.max(...rows.map(row => row[metric])) / 10) * 10 || 1;
    const root = byId('perf-model-bars');
    root.replaceChildren();
    for (const row of rows) {
      const item = make('div', 'lp-model-row');
      item.dataset.model = row.model_id;
      item.dataset.context = context.id;
      item.dataset.split = split;
      item.dataset.metric = metric;
      item.dataset.value = String(row[metric]);
      item.dataset.selected = String(row.selected_by_cv);
      const label = make('div', 'lp-bar-label');
      const name = make('span', 'lp-model-name', modelNames[row.model_id]);
      if (row.selected_by_cv) name.append(make('span', 'lp-selected-label', 'CV selected'));
      label.append(name, make('strong', null, `${fmt(row[metric])}%`));
      const track = make('div', 'lp-track');
      track.setAttribute('aria-hidden', 'true');
      const bar = make('i', `lp-bar${row.selected_by_cv ? ' selected' : ''}`);
      bar.style.width = `${100 * row[metric] / max}%`;
      track.append(bar);
      item.append(label, track);
      root.append(item);
    }

    const lowest = rows.reduce((best, row) => row[metric] < best[metric] ? row : best);
    byId('perf-chart-caption').textContent = `${dtypeNames[dtype]} · ${policyNames[policy]} · ${rows[0].n_cases} shapes · axis 0–${count(max)}%`;
    byId('perf-chart').setAttribute('aria-busy', 'false');
    byId('perf-selected-model').textContent = modelNames[selected.model_id];
    byId('perf-selected-error').textContent = `${fmt(selected[metric])}%`;
    byId('perf-selected-context').textContent = `${splitNames[split]} ${metricNames[metric]} for the training-selected model.`;
    byId('perf-comparison-note').textContent = lowest.model_id === selected.model_id
      ? 'The training-selected model also has the lowest displayed error in this view.'
      : `${modelNames[lowest.model_id]} has the lowest displayed ${metricNames[metric]} (${fmt(lowest[metric])}%). The training-selected model remains fixed.`;
    byId('perf-selection-design').textContent = `${context.cv_folds} folds grouped across ${context.train_family_count} training N/K families; refit on ${context.train_count} shapes. Held-out results never replace the selected model.`;
    byId('perf-cohort-note').textContent = `${scopeNotes[split]} This view contains ${rows[0].n_cases} eligible shapes.`;
    byId('perf-metric-note').textContent = `APE = |predicted − measured| / measured × 100. ${metricNotes[metric]}`;
    byId('perf-live-status').textContent = `${dtypeNames[dtype]} · ${policyNames[policy]} · ${splitNames[split]}: selected ${modelNames[selected.model_id]}, ${fmt(selected[metric])}% ${metricNames[metric]}.`;
  }

  function renderFamily() {
    if (!families) return;
    const family = families.find(row => row.id === byId('perf-family').value);
    if (!family) throw new Error('Unknown shape family.');
    const rotation = byId('perf-sampling-policy').value === 'rotating_buffers';
    const cases = [...family.cases].sort((a, b) => a.m - b.m);
    const eligible = cases.filter(row => !rotation || row.rotation_eligible);
    const repeated = eligible.filter(row => row.repeat).length;
    byId('perf-family-title').textContent = `N = ${count(family.n)} · K = ${count(family.k)}`;
    byId('perf-family-description').textContent = family.kind === 'stress'
      ? 'Artificial irregular dimensions, evaluated only as stress cases.'
      : family.challenge
        ? 'Architecture-derived dimensions. This entire N/K family is held out from training.'
        : 'Architecture-derived dimensions. Training and ordinary-test shapes use different M values.';
    const root = byId('perf-family-cases');
    root.replaceChildren();
    for (const row of cases) {
      const ineligible = rotation && !row.rotation_eligible;
      const cell = make('div', `lp-sampling-case${ineligible ? ' is-ineligible' : ''}`);
      cell.setAttribute('role', 'listitem');
      cell.dataset.case = row.id;
      cell.dataset.split = row.split;
      cell.dataset.m = String(row.m);
      cell.dataset.rotationEligible = String(row.rotation_eligible);
      const description = `M ${count(row.m)}, ${splitNames[row.split]}. ${row.coverage_label || ''}${row.repeat ? ' Predetermined repeat shape.' : ''}${!row.rotation_eligible ? ' Warm reuse only; weight exceeds rotation eligibility limit.' : ''}`;
      cell.setAttribute('aria-label', description);
      cell.title = description;
      const dimension = make('span', 'lp-case-m');
      dimension.append(make('small', null, 'M'), document.createTextNode(count(row.m)));
      cell.append(dimension, make('span', 'lp-case-split', shortSplitNames[row.split]));
      if (row.repeat) {
        const marker = make('span', 'lp-case-repeat', 'R');
        marker.setAttribute('aria-hidden', 'true');
        cell.append(marker);
      }
      if (ineligible) cell.append(make('span', 'lp-case-eligibility', 'Warm only'));
      root.append(cell);
    }
    const omitted = cases.length - eligible.length;
    byId('perf-family-status').textContent = `${eligible.length} shapes eligible for ${rotation ? 'four-buffer rotation' : 'warm reuse'} in this family; ${repeated} belong to the predetermined repeat.${omitted ? ` ${omitted} warm-only shapes remain shown with dashed borders.` : ''}`;
  }

  function renderSampling() {
    const policy = byId('perf-sampling-policy').value;
    const context = contextFor('float16', policy);
    const max = Math.max(...Object.values(data.summary.split_counts));
    byId('perf-sampling-total').textContent = count(context.primary_count);
    byId('perf-sampling-caption').textContent = `Both precisions use this retained cohort. ${context.repeat_count} of its ${context.primary_count} shapes belong to the same-session repeat.`;
    document.querySelectorAll('#perf-sampling-bars [data-split]').forEach(row => {
      const value = context.split_counts[row.dataset.split];
      row.querySelector('b').textContent = count(value);
      row.querySelector('.lp-bar').style.width = `${100 * value / max}%`;
      row.dataset.count = String(value);
    });
    renderFamily();
  }

  function prepareFamilies() {
    if (!data.sampling || !Array.isArray(data.sampling.families) || !data.sampling.families.length) return;
    families = data.sampling.families;
    const select = byId('perf-family');
    select.replaceChildren();
    for (const kind of ['architecture', 'stress']) {
      const group = make('optgroup');
      group.label = kind === 'architecture' ? 'Architecture-derived families' : 'Artificial irregular families';
      for (const family of families.filter(row => row.kind === kind)) {
        const role = family.kind === 'stress' ? 'stress' : family.challenge ? 'challenge' : 'train / test';
        const option = make('option', null, `${count(family.n)} × ${count(family.k)} · ${role}`);
        option.value = family.id;
        group.append(option);
      }
      select.append(group);
    }
    const initial = families.find(row => row.n === 2048 && row.k === 2048)
      || families.find(row => row.kind === 'architecture' && !row.challenge)
      || families[0];
    select.value = initial.id;
    byId('perf-family-inspector').hidden = false;
    select.disabled = false;
    select.addEventListener('change', () => { try { renderFamily(); } catch (error) { showError(error); } });
  }

  function validate(input) {
    const positiveInteger = value => Number.isInteger(value) && value > 0;
    if (!input || input.schema_version !== 2 || !Array.isArray(input.models) || input.models.length !== 5 || !Array.isArray(input.contexts) || input.contexts.length !== 4 || !Array.isArray(input.metrics) || input.metrics.length !== 60) throw new Error('Unexpected result schema.');
    const modelIds = new Set(input.models.map(row => row.id));
    if (modelIds.size !== 5 || input.models.some(row => typeof row.label !== 'string')) throw new Error('Invalid model registry.');
    const contextIds = new Set();
    const contextPolicies = new Set();
    for (const context of input.contexts) {
      const policyKey = `${context.dtype}|${context.cache_policy}`;
      if (contextIds.has(context.id) || contextPolicies.has(policyKey) || !dtypeNames[context.dtype] || !policyNames[context.cache_policy] || !modelIds.has(context.selected_model_id) || !positiveInteger(context.train_count) || !positiveInteger(context.train_family_count) || !positiveInteger(context.cv_folds)) throw new Error('Invalid context registry.');
      if (!context.split_counts || Object.keys(splitNames).some(split => !positiveInteger(context.split_counts[split])) || !positiveInteger(context.primary_count) || !positiveInteger(context.repeat_count)) throw new Error('Invalid context counts.');
      contextIds.add(context.id);
      contextPolicies.add(policyKey);
    }
    const keys = new Set();
    for (const row of input.metrics) {
      const key = `${row.context_id}|${row.split}|${row.model_id}`;
      if (keys.has(key) || !contextIds.has(row.context_id) || !modelIds.has(row.model_id) || !['test', 'challenge', 'stress'].includes(row.split) || !positiveInteger(row.n_cases) || typeof row.selected_by_cv !== 'boolean') throw new Error('Invalid model metric row.');
      if (Object.keys(metricNames).some(metric => !Number.isFinite(row[metric]) || row[metric] < 0)) throw new Error('Invalid error value.');
      keys.add(key);
    }
    for (const context of input.contexts) {
      for (const split of ['test', 'challenge', 'stress']) {
        const group = input.metrics.filter(row => row.context_id === context.id && row.split === split);
        const selected = group.filter(row => row.selected_by_cv);
        if (group.length !== 5 || selected.length !== 1 || selected[0].model_id !== context.selected_model_id || group.some(row => row.n_cases !== context.split_counts[split])) throw new Error('Inconsistent context results.');
      }
    }
    if (!input.summary || !input.summary.split_counts || Object.keys(splitNames).some(split => !positiveInteger(input.summary.split_counts[split]))) throw new Error('Invalid workload counts.');
    if (input.sampling && Array.isArray(input.sampling.families)) {
      const familyIds = new Set();
      for (const family of input.sampling.families) {
        if (familyIds.has(family.id) || !positiveInteger(family.n) || !positiveInteger(family.k) || !['architecture', 'stress'].includes(family.kind) || !Array.isArray(family.cases) || !family.cases.length) throw new Error('Invalid sampling family.');
        familyIds.add(family.id);
        for (const row of family.cases) {
          if (!positiveInteger(row.m) || !splitNames[row.split] || typeof row.repeat !== 'boolean' || typeof row.rotation_eligible !== 'boolean') throw new Error('Invalid sampling case.');
        }
      }
    }
    return input;
  }

  function showError(error) {
    console.error('The recorded-results explorer could not load:', error);
    byId('perf-data-error').hidden = false;
    byId('perf-chart').setAttribute('aria-busy', 'false');
    byId('perf-chart-caption').textContent = 'Interactive comparison unavailable. See the selected-model table below.';
    byId('perf-model-bars').replaceChildren();
    byId('perf-selected-error').textContent = '—';
    byId('perf-selected-context').textContent = 'See the selected-model table for recorded results.';
    byId('perf-comparison-note').textContent = '';
    byId('perf-live-status').textContent = '';
    [...controls, 'perf-sampling-policy', 'perf-family'].forEach(id => { byId(id).disabled = true; });
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  fetch('/assets/linear-perf/results.json?v=1.1.0', { signal: controller.signal })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(input => {
      data = validate(input);
      modelNames = Object.fromEntries(data.models.map(row => [row.id, row.label]));
      metricIndex = new Map(data.metrics.map(row => [`${row.context_id}|${row.split}|${row.model_id}`, row]));
      renderModels();
      prepareFamilies();
      renderSampling();
      controls.forEach(id => {
        byId(id).disabled = false;
        byId(id).addEventListener('change', () => { try { renderModels(); } catch (error) { showError(error); } });
      });
      byId('perf-sampling-policy').disabled = false;
      byId('perf-sampling-policy').addEventListener('change', () => { try { renderSampling(); } catch (error) { showError(error); } });
    })
    .catch(showError)
    .finally(() => window.clearTimeout(timeout));
})();

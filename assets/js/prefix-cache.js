/* Recorded-data explorer; never starts inference or sends user data. */
(function () {
  'use strict';
  const metrics = {
    throughput: { title: 'Output throughput', fields: ['off', 'on'], unit: 'tokens/s', higher: true, note: 'Total output tokens divided by benchmark duration. Gains describe the selected synthetic workload, not a universal model acceleration.' },
    ttft: { title: 'p50 time to first token', fields: ['ttft_off', 'ttft_on'], unit: 'ms', higher: false, note: 'Time from request send to the first output token. Small differences can be within measurement variability; the no-prefix condition is not evidence of a general latency improvement.' },
    tpot: { title: 'Mean time per output token', fields: ['tpot_off', 'tpot_on'], unit: 'ms', higher: false, note: 'Average time per subsequent output token. Under concurrent load, prefill and decode compete for resources. This is not a direct measurement of an isolated decode kernel.' },
    e2e: { title: 'p50 end-to-end latency', fields: ['e2e_off', 'e2e_on'], unit: 'ms', higher: false, note: 'Request send to last token; excludes time waiting in the client-side concurrency queue. This is not scheduled-arrival-to-completion latency.' },
    p99: { title: 'p99 time to first token', fields: ['p99_off', 'p99_on'], unit: 'ms', higher: false, note: 'Median of three per-run p99 values (500 measured requests per run). The initial closed-loop burst affects the tail. This is not a pooled p99, a steady-state tail guarantee, or a production SLO.' }
  };
  function view(row, name) {
    const m = metrics[name];
    if (!m || !row) throw new Error('Unknown recorded-data selection.');
    const a = row[m.fields[0]], b = row[m.fields[1]];
    if (![a,b].every(x => Number.isFinite(x) && x > 0)) throw new Error('Invalid recorded values.');
    const maximum = Math.max(a,b);
    return { ...m, off: a, on: b, widthOff: 100*a/maximum, widthOn: 100*b/maximum,
      ratio: m.higher ? row.gain : a/b,
      ratioLabel: m.higher ? 'THROUGHPUT RATIO' : 'LATENCY RATIO',
      ratioNote: m.higher ? 'Cache on / cache off' : 'Cache off / cache on · above 1 means lower latency with cache on' };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { view, metrics };
  if (typeof document === 'undefined') return;
  const dataEl = document.getElementById('pc-data');
  if (!dataEl) return;
  const byId = name => document.getElementById(name);
  try {
    const data = JSON.parse(dataEl.textContent);
    if (data.schema_version !== 1 || data.rows.length !== 6) throw new Error('Unexpected data schema.');
    const scenario = byId('pc-scenario'), metric = byId('pc-metric');
    const format = (value, unit) => value.toLocaleString('en-US', {minimumFractionDigits:unit==='tokens/s'?1:0,maximumFractionDigits:1});
    function render() {
      const row = data.rows[Number(scenario.value)];
      const v = view(row,metric.value);
      byId('pc-chart-title').textContent = v.title;
      byId('pc-direction').textContent = (v.higher ? 'Higher' : 'Lower') + ' is better · ' + v.unit;
      byId('pc-off-value').textContent = format(v.off,v.unit);
      byId('pc-on-value').textContent = format(v.on,v.unit);
      byId('pc-off-bar').style.width = v.widthOff+'%';
      byId('pc-on-bar').style.width = v.widthOn+'%';
      byId('pc-ratio').textContent = v.ratio.toFixed(2)+'×';
      byId('pc-ratio-label').textContent = v.ratioLabel;
      byId('pc-ratio-note').textContent = v.ratioNote;
      const condition = row.prefix.toLocaleString('en-US')+' shared-prefix tokens · concurrency '+row.concurrency;
      byId('pc-condition').textContent = condition;
      byId('pc-hit').textContent = 'Reported prefix-cache hit rate: '+(100*row.hit_rate).toFixed(2)+'%';
      byId('pc-metric-note').textContent = v.note;
      const spoken = condition+'. '+v.title+': cache off '+format(v.off,v.unit)+', cache on '+format(v.on,v.unit)+' '+v.unit+'.';
      byId('pc-chart').setAttribute('aria-label',spoken);
      byId('pc-status').textContent = spoken+' Medians of three repeats; warm-up excluded.';
    }
    scenario.addEventListener('change',render);
    metric.addEventListener('change',render);
    render();
  } catch (error) {
    ['pc-scenario','pc-metric'].forEach(id=>{const e=byId(id);if(e)e.disabled=true;});
    const e=byId('pc-status');
    if(e)e.textContent='The interactive view is unavailable. The recorded default, full table, CSV, and source report remain available.';
  }
}());

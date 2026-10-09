(() => {
  const derivativeSlider = document.getElementById('x-slider');
  if (!derivativeSlider) return;

  // f(x) and its analytical derivative come from the user's Micrograd notebook.
  const f = x => 3 * x * x - 4 * x + 5;
  const df = x => 6 * x - 4;
  const left = 38, right = 680, top = 20, bottom = 270;
  const minX = -2, maxX = 3, minY = 2.5, maxY = 27;
  const plotX = x => left + (x - minX) / (maxX - minX) * (right - left);
  const plotY = y => bottom - (y - minY) / (maxY - minY) * (bottom - top);
  const line = (x0, y0, x1, y1) => `M ${x0.toFixed(2)} ${y0.toFixed(2)} L ${x1.toFixed(2)} ${y1.toFixed(2)}`;

  const curve = document.getElementById('function-curve');
  const tangent = document.getElementById('tangent-line');
  const point = document.getElementById('function-point');
  const guide = document.getElementById('function-guide');
  const valueX = document.getElementById('x-value');
  const valueY = document.getElementById('y-value');
  const valueGrad = document.getElementById('grad-value');
  const pointLabel = document.getElementById('point-label');
  let x = 2;

  curve.setAttribute('d', Array.from({ length: 151 }, (_, i) => {
    const xx = minX + (maxX - minX) * i / 150;
    return `${i ? 'L' : 'M'} ${plotX(xx).toFixed(2)} ${plotY(f(xx)).toFixed(2)}`;
  }).join(' '));

  function updateCurve() {
    x = Number(derivativeSlider.value);
    const y = f(x), g = df(x);
    const px = plotX(x), py = plotY(y);
    point.setAttribute('cx', px); point.setAttribute('cy', py);
    guide.setAttribute('d', line(px, py, px, bottom));
    const startX = x - .65, endX = x + .65;
    tangent.setAttribute('d', line(plotX(startX), plotY(y + g * (startX - x)), plotX(endX), plotY(y + g * (endX - x))));
    valueX.textContent = x.toFixed(2);
    valueY.textContent = y.toFixed(3);
    valueGrad.textContent = g.toFixed(3);
    pointLabel.textContent = `(${x.toFixed(2)}, ${y.toFixed(2)})`;
    pointLabel.setAttribute('x', Math.min(580, Math.max(52, px + 14)));
    pointLabel.setAttribute('y', Math.max(18, py - 14));
  }
  derivativeSlider.addEventListener('input', updateCurve);
  document.getElementById('gradient-step')?.addEventListener('click', () => {
    derivativeSlider.value = String(Math.max(minX, Math.min(maxX, x - .055 * df(x))));
    updateCurve();
  });
  document.getElementById('gradient-reset')?.addEventListener('click', () => {
    derivativeSlider.value = '2'; updateCurve();
  });
  updateCurve();

  // One neuron from the notebook: o = tanh(x1*w1 + x2*w2 + b), with x2=0, w2=1.
  const neuronFields = [...document.querySelectorAll('[data-neuron-input]')];
  const neuronOutput = document.getElementById('neuron-output');
  function updateNeuron() {
    const values = {};
    neuronFields.forEach(el => {
      const value = Number(el.value);
      values[el.dataset.neuronInput] = value;
      const label = document.querySelector(`[data-neuron-readout="${el.dataset.neuronInput}"]`);
      if (label) label.textContent = value.toFixed(2);
    });
    const z = values.x1 * values.w1 + values.b; // x2=0, w2=1 in this demonstration.
    const o = Math.tanh(z);
    const local = 1 - o * o;
    const outputs = {
      'neuron-input-val': values.x1.toFixed(2),
      'neuron-product-val': (values.x1 * values.w1).toFixed(2),
      'neuron-sum-val': z.toFixed(2),
      'neuron-output-val': o.toFixed(4),
      'grad-x1': (local * values.w1).toFixed(4),
      'grad-w1': (local * values.x1).toFixed(4),
      'grad-b': local.toFixed(4),
    };
    Object.entries(outputs).forEach(([id, v]) => { const el = document.getElementById(id); if (el) el.textContent = v; });
    neuronOutput?.setAttribute('aria-label', `Neuron output ${o.toFixed(4)}`);
  }
  neuronFields.forEach(el => el.addEventListener('input', updateNeuron));
  updateNeuron();

  // Verbatim numeric output from one saved notebook training log (20 displayed iterations).
  // It is not a benchmark and may differ across reruns because no random seed was fixed.
  const losses = [
    0.007439767063559038, 0.007290012833750416, 0.007145895226623924,
    0.0070071078722018796, 0.00687336597429526, 0.006744404457329734,
    0.006619976300054436, 0.006499851034588007, 0.006383813392041607,
    0.006271662078345164, 0.006163208665956007, 0.006058276588895456,
    0.005956700230085873, 0.005858324091282143, 0.005763002037036681,
    0.005670596605134646, 0.005580978376803244, 0.005494025400757364,
    0.00540962266580632, 0.005327661617327891
  ];
  const lossLine = document.getElementById('loss-line');
  const lossFill = document.getElementById('loss-fill');
  const lx0 = 38, lx1 = 680, ly0 = 25, ly1 = 205;
  const lo = Math.min(...losses) - .00025, hi = Math.max(...losses) + .00025;
  const points = losses.map((v, i) => [lx0 + i / (losses.length - 1) * (lx1 - lx0), ly1 - (v - lo) / (hi - lo) * (ly1 - ly0)]);
  const d = points.map(([xx, yy], i) => `${i === 0 ? 'M' : 'L'} ${xx.toFixed(2)} ${yy.toFixed(2)}`).join(' ');
  lossLine?.setAttribute('d', d);
  lossFill?.setAttribute('d', `${d} L ${lx1} ${ly1} L ${lx0} ${ly1} Z`);
  const lastPoint = points[points.length-1];
  document.getElementById('loss-end-point')?.setAttribute('cx', lastPoint[0]);
  document.getElementById('loss-end-point')?.setAttribute('cy', lastPoint[1]);
})();

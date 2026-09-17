(async function () {
  const tabsEl = document.getElementById('tabs');
  const formEl = document.getElementById('param-form');
  const runBtn = document.getElementById('run-btn');
  const errorBox = document.getElementById('error-box');
  const summaryText = document.getElementById('summary-text');
  const resultPlot = document.getElementById('result-plot');
  const tooltip = document.getElementById('tooltip');
  const scoreBtn = document.getElementById('score-btn');
  const scoreSummary = document.getElementById('score-summary');
  const scoreValue = document.getElementById('score-value');
  const scoreVerdict = document.getElementById('score-verdict');
  const scoreBarTrack = document.getElementById('score-bar-track');
  const scoreBarFill = document.getElementById('score-bar-fill');
  const scoreChecks = document.getElementById('score-checks');

  // Mirrors webapp/schematic_graph.py ANALYSIS_TO_SUBSYSTEM.
  const ANALYSIS_TO_SUBSYSTEM = {
    power_tree: 'power_tree',
    modem_burst: 'modem_burst',
    autoreset: 'autoreset',
    pwrkey: 'pwrkey',
    haptics: 'haptics',
    led: 'leds',
    usb_cc: 'usb_cc',
  };

  let analyses = [];
  let currentAnalysis = null;
  let cy = null;
  let overlayNodeIds = [];

  function formatValue(v) {
    if (typeof v !== 'number') return String(v);
    return Math.abs(v) < 0.01 && v !== 0 ? v.toExponential(3) : v.toFixed(3);
  }

  function colorForValue(value, min, max) {
    if (min === max) return 'hsl(140, 70%, 45%)';
    const t = (value - min) / (max - min);
    const hue = 210 - t * 210;
    return `hsl(${hue}, 75%, 45%)`;
  }

  // Fixed semantic bands (not min/max normalized) so a score's color means
  // the same thing every time you look at it, matching scoring.py's verdict
  // thresholds.
  function scoreColor(pct) {
    if (pct >= 90) return '#16a34a';
    if (pct >= 70) return '#ca8a04';
    if (pct >= 40) return '#ea580c';
    return '#dc2626';
  }

  async function computeBoardScore() {
    scoreBtn.disabled = true;
    scoreBtn.textContent = 'Computing…';
    try {
      const res = await fetch('/api/score');
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
      }
      const color = scoreColor(data.overall_score);
      scoreSummary.classList.remove('hidden');
      scoreBarTrack.classList.remove('hidden');
      scoreChecks.classList.remove('hidden');
      scoreValue.textContent = `${data.overall_score.toFixed(1)}%`;
      scoreValue.style.color = color;
      scoreVerdict.textContent = data.verdict;
      scoreBarFill.style.width = `${data.overall_score}%`;
      scoreBarFill.style.backgroundColor = color;

      scoreChecks.innerHTML = '';
      data.checks.forEach((c) => {
        const li = document.createElement('li');
        li.style.borderLeftColor = scoreColor(c.score_pct);
        const strong = document.createElement('strong');
        strong.textContent = `${c.label} (${c.score_pct.toFixed(1)}%)`;
        const detail = document.createElement('span');
        detail.className = 'check-detail';
        detail.textContent = c.detail;
        li.appendChild(strong);
        li.appendChild(detail);
        scoreChecks.appendChild(li);
      });
    } catch (err) {
      scoreSummary.classList.remove('hidden');
      scoreValue.textContent = '--%';
      scoreVerdict.textContent = err.message;
    } finally {
      scoreBtn.disabled = false;
      scoreBtn.textContent = 'Recompute board health score';
    }
  }

  function clearOverlay() {
    overlayNodeIds.forEach((id) => {
      const n = cy.getElementById(id);
      if (n.nonempty()) {
        n.removeStyle('background-color');
        n.removeData('value');
      }
    });
    overlayNodeIds = [];
  }

  function applyOverlay(overlay) {
    clearOverlay();
    const values = Object.values(overlay);
    if (!values.length) return;
    const min = Math.min(...values);
    const max = Math.max(...values);
    Object.entries(overlay).forEach(([id, value]) => {
      const n = cy.getElementById(id);
      if (n.empty()) return;
      n.data('value', value);
      n.style('background-color', colorForValue(value, min, max));
      overlayNodeIds.push(id);
    });
  }

  function dimAllExcept(subsystem) {
    cy.elements().addClass('dimmed');
    const group = cy.getElementById(`group:${subsystem}`);
    group.removeClass('dimmed');
    group.descendants().removeClass('dimmed');
  }

  function renderTabs() {
    tabsEl.innerHTML = '';
    analyses.forEach((a) => {
      const btn = document.createElement('button');
      btn.textContent = a.label;
      btn.type = 'button';
      btn.dataset.name = a.name;
      btn.addEventListener('click', () => selectAnalysis(a.name));
      tabsEl.appendChild(btn);
    });
  }

  function updateTabActiveState() {
    [...tabsEl.children].forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.name === currentAnalysis.name);
    });
  }

  function renderForm() {
    formEl.innerHTML = '';
    currentAnalysis.params.forEach((p) => {
      const row = document.createElement('label');
      row.className = 'param-row';
      const text = document.createElement('span');
      text.textContent = `${p.label}${p.unit ? ' (' + p.unit + ')' : ''}`;
      const input = document.createElement('input');
      input.type = 'number';
      input.name = p.name;
      input.min = String(p.min);
      input.max = String(p.max);
      input.step = p.step != null ? String(p.step) : 'any';
      input.value = String(p.default);
      row.appendChild(text);
      row.appendChild(input);
      formEl.appendChild(row);
    });
  }

  function clearResults() {
    errorBox.classList.add('hidden');
    errorBox.textContent = '';
    summaryText.textContent = '';
    resultPlot.classList.add('hidden');
    resultPlot.removeAttribute('src');
  }

  function formatSummary(summary) {
    const lines = [];
    Object.entries(summary).forEach(([key, value]) => {
      if (value && typeof value === 'object') {
        lines.push(`${key}:`);
        Object.entries(value).forEach(([k, v]) => {
          lines.push(`  ${k}: ${formatValue(v)}`);
        });
      } else {
        lines.push(`${key}: ${formatValue(value)}`);
      }
    });
    return lines.join('\n');
  }

  function selectAnalysis(name) {
    currentAnalysis = analyses.find((a) => a.name === name);
    updateTabActiveState();
    renderForm();
    clearResults();
    clearOverlay();
    dimAllExcept(ANALYSIS_TO_SUBSYSTEM[name]);
  }

  async function runCurrentAnalysis() {
    clearResults();
    runBtn.disabled = true;
    runBtn.textContent = 'Running…';
    try {
      const body = {};
      [...formEl.elements].forEach((el) => {
        if (el.name) body[el.name] = parseFloat(el.value);
      });
      const res = await fetch(`/api/run/${currentAnalysis.name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
      }
      summaryText.textContent = formatSummary(data.summary);
      if (data.plot_png_base64) {
        resultPlot.src = `data:image/png;base64,${data.plot_png_base64}`;
        resultPlot.classList.remove('hidden');
      }
      applyOverlay(data.overlay || {});
    } catch (err) {
      errorBox.textContent = err.message;
      errorBox.classList.remove('hidden');
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = 'Run';
    }
  }

  function showTooltip(node, evt) {
    const label = node.data('label');
    const value = node.data('value');
    tooltip.textContent = value !== undefined ? `${label}: ${formatValue(value)}` : label;
    tooltip.classList.remove('hidden');
    const orig = evt.originalEvent;
    if (orig) {
      tooltip.style.left = `${orig.clientX + 12}px`;
      tooltip.style.top = `${orig.clientY + 12}px`;
    }
  }

  // Cytoscape renders to a <canvas>, so it ignores the page's CSS dark-mode
  // rules entirely -- node/edge colors have to be picked in JS and re-applied
  // on theme change, or labels default to black-on-black in dark mode.
  function buildCytoscapeStyle() {
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const palette = dark
      ? {
          groupLabel: '#cbd5e1',
          groupBorder: '#64748b',
          groupFill: '#3b82f6',
          groupOpacity: 0.12,
          netBg: '#38bdf8',
          netLabel: '#e2e8f0',
          componentBg: '#64748b',
          componentBorder: '#94a3b8',
          componentLabel: '#e2e8f0',
          edgeColor: '#71809b',
        }
      : {
          groupLabel: '#475569',
          groupBorder: '#94a3b8',
          groupFill: '#2563eb',
          groupOpacity: 0.06,
          netBg: '#64748b',
          netLabel: '#334155',
          componentBg: '#cbd5e1',
          componentBorder: '#94a3b8',
          componentLabel: '#334155',
          edgeColor: '#94a3b8',
        };

    return [
      {
        selector: 'node[kind = "group"]',
        style: {
          shape: 'round-rectangle',
          'background-opacity': palette.groupOpacity,
          'background-color': palette.groupFill,
          'border-width': 1,
          'border-color': palette.groupBorder,
          label: 'data(label)',
          'text-valign': 'top',
          'text-halign': 'left',
          'font-size': 11,
          color: palette.groupLabel,
          padding: '18px',
        },
      },
      {
        selector: 'node[kind = "net"]',
        style: {
          shape: 'ellipse',
          width: 16,
          height: 16,
          'background-color': palette.netBg,
          label: 'data(label)',
          'font-size': 8,
          color: palette.netLabel,
          'text-valign': 'bottom',
          'text-margin-y': 4,
        },
      },
      {
        selector: 'node[kind = "component"], node[kind = "ic"]',
        style: {
          shape: 'round-rectangle',
          width: 14,
          height: 14,
          'background-color': palette.componentBg,
          'border-width': 1,
          'border-color': palette.componentBorder,
          label: 'data(label)',
          'font-size': 7,
          color: palette.componentLabel,
          'text-valign': 'bottom',
          'text-margin-y': 3,
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.2,
          'line-color': palette.edgeColor,
          'curve-style': 'bezier',
          'target-arrow-shape': 'none',
        },
      },
      {
        selector: '.dimmed',
        style: { opacity: 0.15 },
      },
    ];
  }

  function initCytoscape(elements) {
    cy = cytoscape({
      container: document.getElementById('cy'),
      elements,
      layout: { name: 'preset' },
      style: buildCytoscapeStyle(),
    });

    // Inline overlay colors (applied via ele.style() after a run) survive a
    // cy.style() stylesheet swap, so this is safe to do live.
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      cy.style(buildCytoscapeStyle()).update();
    });

    cy.on('mouseover', 'node[kind != "group"]', (evt) => showTooltip(evt.target, evt));
    cy.on('mouseout', 'node', () => tooltip.classList.add('hidden'));
    cy.on('tap', 'node[kind != "group"]', (evt) => showTooltip(evt.target, evt));
  }

  const [schematic, analysesResp] = await Promise.all([
    fetch('/api/schematic').then((r) => r.json()),
    fetch('/api/analyses').then((r) => r.json()),
  ]);

  analyses = analysesResp;
  initCytoscape([...schematic.nodes, ...schematic.edges]);
  renderTabs();
  selectAnalysis(analyses[0].name);

  runBtn.addEventListener('click', runCurrentAnalysis);
  scoreBtn.addEventListener('click', computeBoardScore);
})();

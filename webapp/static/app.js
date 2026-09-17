(function () {
  "use strict";

  var navData = JSON.parse(document.getElementById("nav-data").textContent);
  var content = document.getElementById("content");
  var navEl = document.getElementById("nav");

  var GROUP_ORDER = ["Diagrams", "Analysis", "Source Data", "Screenshots", "Simulation"];

  var items = [];
  var sourcePathToRoute = {};
  navData.docs.forEach(function (d) {
    items.push({ kind: "doc", key: d.key, title: d.title, group: d.group, tag: "MD" });
    sourcePathToRoute[d.source] = "doc:" + d.key;
  });
  items.push({ kind: "diagrams", key: "diagrams", title: "PCB Visualization", group: "Diagrams", tag: "DGM" });
  navData.data.forEach(function (d) {
    items.push({ kind: "json", key: d.key, title: d.title, group: "Source Data", tag: "JSON" });
  });
  navData.images.forEach(function (d) {
    items.push({ kind: "img", key: d.key, title: d.title, group: "Screenshots", tag: "IMG" });
  });
  items.push({ kind: "sim", key: "sim", title: "Circuit Simulator", group: "Simulation", tag: "SIM" });

  var itemsByRoute = {};
  items.forEach(function (it) { itemsByRoute[it.kind + ":" + it.key] = it; });

  // ---------- Nav rendering ----------

  function buildNav() {
    var html = "";
    GROUP_ORDER.forEach(function (group) {
      var groupItems = items.filter(function (it) { return it.group === group; });
      if (!groupItems.length) return;
      html += '<div class="nav-group" data-group="' + group + '"><h2>' + group + "</h2>";
      groupItems.forEach(function (it) {
        var route = it.kind + ":" + it.key;
        html += '<button class="nav-item" data-route="' + route + '" type="button">' +
          '<span class="tag tag-' + it.kind + '">' + it.tag + "</span>" +
          "<span>" + escapeHtml(it.title) + "</span></button>";
      });
      html += "</div>";
    });
    navEl.innerHTML = html;
    navEl.addEventListener("click", function (e) {
      var btn = e.target.closest(".nav-item");
      if (!btn) return;
      location.hash = btn.dataset.route;
      closeMobileNav();
    });
  }

  function setActiveNav(route) {
    var buttons = navEl.querySelectorAll(".nav-item");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.toggle("active", buttons[i].dataset.route === route);
    }
  }

  // ---------- Filter ----------

  document.getElementById("nav-search").addEventListener("input", function (e) {
    var q = e.target.value.trim().toLowerCase();
    var groups = navEl.querySelectorAll(".nav-group");
    groups.forEach(function (g) {
      var visibleCount = 0;
      g.querySelectorAll(".nav-item").forEach(function (btn) {
        var match = !q || btn.textContent.toLowerCase().indexOf(q) !== -1;
        btn.hidden = !match;
        if (match) visibleCount++;
      });
      g.hidden = visibleCount === 0;
    });
  });

  // ---------- Rendering helpers ----------

  function escapeHtml(s) {
    return String(s).replace(/[&<>]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
    });
  }

  function sheetShell(badge, badgeKind, metaHtml, bodyHtml) {
    return '<div class="sheet" data-badge="' + badge + '" data-badge-kind="' + badgeKind + '">' +
      '<div class="sheet-meta">' + metaHtml + "</div>" +
      bodyHtml +
      "</div>";
  }

  function setContent(html) {
    content.innerHTML = html;
    content.focus();
  }

  // Resolve an href found inside a rendered doc relative to that doc's
  // own project-root-relative path (e.g. "analysis/06-images.md" + "03-x.md"
  // -> "analysis/03-x.md"), the same way a browser would resolve a relative
  // link -- so cross-doc markdown links keep working inside the SPA router.
  function resolveRelativePath(baseSource, href) {
    var stack = baseSource.split("/").slice(0, -1);
    href.split("/").forEach(function (part) {
      if (part === "" || part === ".") return;
      if (part === "..") stack.pop();
      else stack.push(part);
    });
    return stack.join("/");
  }

  var currentDocSource = null;

  content.addEventListener("click", function (e) {
    var a = e.target.closest(".doc a");
    if (!a || !currentDocSource) return;
    var href = a.getAttribute("href") || "";
    if (/^([a-z]+:)?\/\//i.test(href) || href.indexOf("mailto:") === 0) return;
    var hashIdx = href.indexOf("#");
    var pathPart = hashIdx === -1 ? href : href.slice(0, hashIdx);
    if (!pathPart) return; // pure same-page anchor, let the browser handle it
    var resolved = resolveRelativePath(currentDocSource, pathPart);
    var route = sourcePathToRoute[resolved];
    if (route) {
      e.preventDefault();
      location.hash = route;
    }
  });

  // ---------- JSON syntax highlight ----------

  function highlightJson(jsonText) {
    var escaped = escapeHtml(jsonText);
    return escaped.replace(
      /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
      function (match) {
        var cls = "jn";
        if (/^"/.test(match)) {
          cls = /:\s*$/.test(match) ? "jk" : "js";
        } else if (/true|false|null/.test(match)) {
          cls = "jb";
        }
        return '<span class="' + cls + '">' + match + "</span>";
      }
    );
  }

  // ---------- Route renderers ----------

  function renderDoc(key) {
    setContent('<div class="empty">Loading document…</div>');
    fetch("/api/doc/" + key + ".json").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      currentDocSource = data.source;
      var meta = "<span>SOURCE: <b>" + escapeHtml(data.source) + "</b></span>" +
        '<span><a href="/raw/doc/' + key + '.md" target="_blank" rel="noopener">view raw markdown ↗</a></span>';
      setContent(sheetShell("MD", "md", meta, '<div class="doc">' + data.html + "</div>"));
    }).catch(function (err) {
      setContent('<div class="empty">Could not load this document (' + escapeHtml(err.message) + ").</div>");
    });
  }

  function renderJson(key) {
    setContent('<div class="empty">Loading + pretty-printing JSON…</div>');
    fetch("/api/json/" + key + ".json").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      var meta = "<span>SOURCE: <b>" + escapeHtml(data.source) + "</b></span>" +
        "<span>SIZE: <b>" + data.size.toLocaleString() + " B</b></span>" +
        '<span><a href="/raw/json/' + key + '.json" target="_blank" rel="noopener">open raw file ↗</a></span>';
      var body = '<p style="color:var(--ink-soft); margin-top:0;">' + escapeHtml(data.note) + "</p>" +
        '<pre class="json-pre">' + highlightJson(data.pretty) + "</pre>";
      setContent(sheetShell("JSON", "json", meta, body));
    }).catch(function (err) {
      setContent('<div class="empty">Could not load this file (' + escapeHtml(err.message) + ").</div>");
    });
  }

  function renderImg(key, title) {
    var src = "/image/" + key + ".jpeg";
    var meta = "<span>FILE: <b>" + escapeHtml(title) + "</b></span>" +
      '<span><a href="' + src + '" target="_blank" rel="noopener">open full size ↗</a></span>';
    var body = '<div class="img-frame"><img src="' + src + '" alt="' + escapeHtml(title) + '"></div>';
    setContent(sheetShell("IMG", "img", meta, body));
  }

  var diagramsFrame = null;

  function renderDiagrams() {
    var meta = "<span>SOURCE: <b>analysis/visualization.html</b></span>" +
      '<span><a href="/diagrams" target="_blank" rel="noopener">open full page ↗</a></span>';
    var body = '<div class="embed-frame"><iframe id="diagrams-iframe" src="/diagrams" title="PCB Visualization"></iframe></div>';
    setContent(sheetShell("DIAGRAMS", "img", meta, body));
    diagramsFrame = document.getElementById("diagrams-iframe");
    diagramsFrame.addEventListener("load", function () { applyThemeToDiagrams(); });
  }

  function renderSim() {
    if (navData.simulationOrigin) {
      renderSimLive();
    } else {
      renderSimStatic();
    }
  }

  // ---- Live mode (local dev only): probe/embed the real simulation server ----

  function renderSimLive() {
    setContent('<div class="empty">Checking for a running simulation server…</div>');
    probeSimulation(function (ok) {
      if (ok) {
        var meta = "<span>ORIGIN: <b>" + navData.simulationOrigin + "</b></span>" +
          '<span><a href="' + navData.simulationOrigin + '" target="_blank" rel="noopener">open in new tab ↗</a></span>';
        var body = '<div class="embed-frame"><iframe src="' + navData.simulationOrigin +
          '" title="Circuit Simulator"></iframe></div>';
        setContent(sheetShell("LIVE", "sim", meta, body));
      } else {
        setContent(
          '<div class="sim-offline">' +
          "<b>Simulation server not running</b>" +
          "<p>The PySpice circuit simulator is a separate process (it needs the " +
          "ngspice shared library) and isn't started automatically. Launch it, " +
          "then retry.</p>" +
          "<pre>pip3 install -r simulation/requirements.txt\npython3 simulation/webapp/app.py</pre>" +
          "<p>Then this tab will embed it from <code>" + navData.simulationOrigin + "</code>.</p>" +
          '<button id="sim-retry" type="button">Retry</button>' +
          "</div>"
        );
        var retryBtn = document.getElementById("sim-retry");
        if (retryBtn) retryBtn.addEventListener("click", renderSim);
      }
    });
  }

  function probeSimulation(callback) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 1500);
    fetch(navData.simulationOrigin, { mode: "no-cors", signal: controller.signal })
      .then(function () { clearTimeout(timer); callback(true); })
      .catch(function () { clearTimeout(timer); callback(false); });
  }

  // ---- Static mode (Netlify build): pre-baked fixtures, no live server ----

  var SIM_DATA_BASE = "/static/sim-data";
  var simStaticState = { loaded: false, schematic: null, analyses: null, score: null, cy: null, current: null, overlayIds: [] };

  function formatSimValue(v) {
    if (typeof v !== "number") return String(v);
    return Math.abs(v) < 0.01 && v !== 0 ? v.toExponential(3) : v.toFixed(3);
  }

  function simColorForValue(value, min, max) {
    if (min === max) return "hsl(140, 70%, 45%)";
    var t = (value - min) / (max - min);
    return "hsl(" + (210 - t * 210) + ", 75%, 45%)";
  }

  function renderSimStatic() {
    if (simStaticState.loaded) {
      paintSimStatic();
      return;
    }
    setContent('<div class="empty">Loading simulation fixtures…</div>');
    Promise.all([
      fetch(SIM_DATA_BASE + "/schematic.json").then(function (r) { return r.json(); }),
      fetch(SIM_DATA_BASE + "/analyses.json").then(function (r) { return r.json(); }),
    ]).then(function (results) {
      simStaticState.schematic = results[0];
      simStaticState.analyses = results[1];
      simStaticState.loaded = true;
      paintSimStatic();
    }).catch(function (err) {
      setContent('<div class="empty">Could not load simulation fixtures (' + escapeHtml(err.message) + ").</div>");
    });
  }

  function paintSimStatic() {
    var meta = "<span>SOURCE: <b>webapp/static/sim-data</b> (built by simulation/webapp/build_fixtures.py)</span>";
    var body =
      '<div class="sim-embed">' +
      '<div class="sim-note">Static build — these are the 7 analyses run once, at build time, ' +
      "with their default parameters (see <code>simulation/webapp/build_fixtures.py</code>). " +
      "Parameter fields below are read-only. To tweak values and re-run live:" +
      "<pre>pip3 install -r simulation/requirements.txt\npython3 simulation/webapp/app.py</pre></div>" +
      '<section id="score-panel">' +
      '<div class="score-header">' +
      '<button id="score-btn" type="button">Show board health score</button>' +
      '<div id="score-summary" class="hidden"><span id="score-value">--%</span><span id="score-verdict"></span></div>' +
      "</div>" +
      '<p class="score-caveat">Heuristic margin score against typical-operation thresholds, computed ' +
      "from all 7 analyses at their nominal/default parameters — not a certified reliability estimate.</p>" +
      '<div id="score-bar-track" class="hidden"><div id="score-bar-fill"></div></div>' +
      '<ul id="score-checks" class="hidden"></ul>' +
      "</section>" +
      '<nav id="tabs" aria-label="Analysis selector"></nav>' +
      '<main class="sim-main">' +
      '<section id="schematic-panel"><div id="cy"></div><div id="tooltip" class="tooltip hidden"></div></section>' +
      '<section id="control-panel">' +
      '<form id="param-form"></form>' +
      '<div id="error-box" class="error hidden"></div>' +
      '<div id="results"><pre id="summary-text"></pre><img id="result-plot" class="hidden" alt="Waveform plot"></div>' +
      "</section>" +
      "</main>" +
      "</div>";
    setContent(sheetShell("STATIC", "sim", meta, body));
    initSimStatic();
  }

  function initSimStatic() {
    var schematic = simStaticState.schematic;
    var analyses = simStaticState.analyses;

    simStaticState.cy = cytoscape({
      container: document.getElementById("cy"),
      elements: schematic.nodes.concat(schematic.edges),
      layout: { name: "preset" },
      style: buildSimCytoscapeStyle(),
    });

    var cy = simStaticState.cy;
    var tooltip = document.getElementById("tooltip");
    function showSimTooltip(node, evt) {
      var label = node.data("label");
      var value = node.data("value");
      tooltip.textContent = value !== undefined ? label + ": " + formatSimValue(value) : label;
      tooltip.classList.remove("hidden");
      var orig = evt.originalEvent;
      if (orig) {
        tooltip.style.left = orig.clientX + 12 + "px";
        tooltip.style.top = orig.clientY + 12 + "px";
      }
    }
    cy.on("mouseover", 'node[kind != "group"]', function (evt) { showSimTooltip(evt.target, evt); });
    cy.on("mouseout", "node", function () { tooltip.classList.add("hidden"); });
    cy.on("tap", 'node[kind != "group"]', function (evt) { showSimTooltip(evt.target, evt); });

    var tabsEl = document.getElementById("tabs");
    tabsEl.innerHTML = "";
    analyses.forEach(function (a) {
      var btn = document.createElement("button");
      btn.textContent = a.label;
      btn.type = "button";
      btn.dataset.name = a.name;
      btn.addEventListener("click", function () { selectSimAnalysis(a.name); });
      tabsEl.appendChild(btn);
    });

    var scoreBtn = document.getElementById("score-btn");
    scoreBtn.addEventListener("click", showSimScore);

    selectSimAnalysis(analyses[0].name);
  }

  function buildSimCytoscapeStyle() {
    var dark = (localStorage.getItem(THEME_KEY) || "auto") === "dark" ||
      ((localStorage.getItem(THEME_KEY) || "auto") === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var palette = dark
      ? { groupLabel: "#cbd5e1", groupBorder: "#64748b", groupFill: "#3b82f6", groupOpacity: 0.12,
          netBg: "#38bdf8", netLabel: "#e2e8f0", componentBg: "#64748b", componentBorder: "#94a3b8",
          componentLabel: "#e2e8f0", edgeColor: "#71809b" }
      : { groupLabel: "#475569", groupBorder: "#94a3b8", groupFill: "#2563eb", groupOpacity: 0.06,
          netBg: "#64748b", netLabel: "#334155", componentBg: "#cbd5e1", componentBorder: "#94a3b8",
          componentLabel: "#334155", edgeColor: "#94a3b8" };
    return [
      { selector: 'node[kind = "group"]', style: {
          shape: "round-rectangle", "background-opacity": palette.groupOpacity, "background-color": palette.groupFill,
          "border-width": 1, "border-color": palette.groupBorder, label: "data(label)",
          "text-valign": "top", "text-halign": "left", "font-size": 11, color: palette.groupLabel, padding: "18px" } },
      { selector: 'node[kind = "net"]', style: {
          shape: "ellipse", width: 16, height: 16, "background-color": palette.netBg, label: "data(label)",
          "font-size": 8, color: palette.netLabel, "text-valign": "bottom", "text-margin-y": 4 } },
      { selector: 'node[kind = "component"], node[kind = "ic"]', style: {
          shape: "round-rectangle", width: 14, height: 14, "background-color": palette.componentBg,
          "border-width": 1, "border-color": palette.componentBorder, label: "data(label)", "font-size": 7,
          color: palette.componentLabel, "text-valign": "bottom", "text-margin-y": 3 } },
      { selector: "edge", style: { width: 1.2, "line-color": palette.edgeColor, "curve-style": "bezier", "target-arrow-shape": "none" } },
      { selector: ".dimmed", style: { opacity: 0.15 } },
    ];
  }

  function dimAllSimExcept(subsystem) {
    var cy = simStaticState.cy;
    cy.elements().addClass("dimmed");
    var group = cy.getElementById("group:" + subsystem);
    group.removeClass("dimmed");
    group.descendants().removeClass("dimmed");
  }

  function clearSimOverlay() {
    var cy = simStaticState.cy;
    simStaticState.overlayIds.forEach(function (id) {
      var n = cy.getElementById(id);
      if (n.nonempty()) { n.removeStyle("background-color"); n.removeData("value"); }
    });
    simStaticState.overlayIds = [];
  }

  function applySimOverlay(overlay) {
    clearSimOverlay();
    var values = Object.values(overlay || {});
    if (!values.length) return;
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    Object.entries(overlay).forEach(function (entry) {
      var id = entry[0], value = entry[1];
      var n = simStaticState.cy.getElementById(id);
      if (n.empty()) return;
      n.data("value", value);
      n.style("background-color", simColorForValue(value, min, max));
      simStaticState.overlayIds.push(id);
    });
  }

  var ANALYSIS_TO_SUBSYSTEM = {
    power_tree: "power_tree", modem_burst: "modem_burst", autoreset: "autoreset",
    pwrkey: "pwrkey", haptics: "haptics", led: "leds", usb_cc: "usb_cc",
  };

  function selectSimAnalysis(name) {
    var analysis = simStaticState.analyses.find(function (a) { return a.name === name; });
    simStaticState.current = analysis;

    var tabsEl = document.getElementById("tabs");
    Array.prototype.forEach.call(tabsEl.children, function (btn) {
      btn.classList.toggle("active", btn.dataset.name === name);
    });

    var formEl = document.getElementById("param-form");
    formEl.innerHTML = "";
    analysis.params.forEach(function (p) {
      var row = document.createElement("label");
      row.className = "param-row";
      var text = document.createElement("span");
      text.textContent = p.label + (p.unit ? " (" + p.unit + ")" : "");
      var input = document.createElement("input");
      input.type = "number";
      input.value = String(p.default);
      input.disabled = true;
      row.appendChild(text);
      row.appendChild(input);
      formEl.appendChild(row);
    });

    document.getElementById("error-box").classList.add("hidden");
    document.getElementById("summary-text").textContent = "Loading result…";
    document.getElementById("result-plot").classList.add("hidden");
    clearSimOverlay();
    dimAllSimExcept(ANALYSIS_TO_SUBSYSTEM[name]);

    fetch(SIM_DATA_BASE + "/results/" + name + ".json").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      if (simStaticState.current !== analysis) return; // superseded by another tab click
      var lines = [];
      Object.entries(data.summary).forEach(function (entry) {
        var key = entry[0], value = entry[1];
        if (value && typeof value === "object") {
          lines.push(key + ":");
          Object.entries(value).forEach(function (e2) { lines.push("  " + e2[0] + ": " + formatSimValue(e2[1])); });
        } else {
          lines.push(key + ": " + formatSimValue(value));
        }
      });
      document.getElementById("summary-text").textContent = lines.join("\n");
      if (data.plot_url) {
        var img = document.getElementById("result-plot");
        img.src = SIM_DATA_BASE + "/" + data.plot_url;
        img.classList.remove("hidden");
      }
      applySimOverlay(data.overlay || {});
    }).catch(function (err) {
      var box = document.getElementById("error-box");
      box.textContent = err.message;
      box.classList.remove("hidden");
    });
  }

  function showSimScore() {
    var btn = document.getElementById("score-btn");
    btn.disabled = true;
    btn.textContent = "Loading…";
    fetch(SIM_DATA_BASE + "/score.json").then(function (r) { return r.json(); }).then(function (data) {
      var color = data.overall_score >= 90 ? "#16a34a" : data.overall_score >= 70 ? "#ca8a04" :
        data.overall_score >= 40 ? "#ea580c" : "#dc2626";
      document.getElementById("score-summary").classList.remove("hidden");
      document.getElementById("score-bar-track").classList.remove("hidden");
      document.getElementById("score-checks").classList.remove("hidden");
      var valueEl = document.getElementById("score-value");
      valueEl.textContent = data.overall_score.toFixed(1) + "%";
      valueEl.style.color = color;
      document.getElementById("score-verdict").textContent = data.verdict;
      var fill = document.getElementById("score-bar-fill");
      fill.style.width = data.overall_score + "%";
      fill.style.backgroundColor = color;

      var checksEl = document.getElementById("score-checks");
      checksEl.innerHTML = "";
      data.checks.forEach(function (c) {
        var li = document.createElement("li");
        li.style.borderLeftColor = color;
        var strong = document.createElement("strong");
        strong.textContent = c.label + " (" + c.score_pct.toFixed(1) + "%)";
        var detail = document.createElement("span");
        detail.className = "check-detail";
        detail.textContent = c.detail;
        li.appendChild(strong);
        li.appendChild(detail);
        checksEl.appendChild(li);
      });
      btn.textContent = "Show board health score";
      btn.disabled = false;
    }).catch(function (err) {
      document.getElementById("score-summary").classList.remove("hidden");
      document.getElementById("score-verdict").textContent = err.message;
      btn.textContent = "Show board health score";
      btn.disabled = false;
    });
  }

  // ---------- Router ----------

  function route() {
    var hash = location.hash.replace(/^#/, "") || "diagrams:diagrams";
    var item = itemsByRoute[hash];
    if (!item) {
      hash = "diagrams:diagrams";
      item = itemsByRoute[hash];
    }
    setActiveNav(hash);
    document.title = item.title + " · Giacomo Dashboard";

    if (item.kind === "doc") renderDoc(item.key);
    else if (item.kind === "json") renderJson(item.key);
    else if (item.kind === "img") renderImg(item.key, item.title);
    else if (item.kind === "diagrams") renderDiagrams();
    else if (item.kind === "sim") renderSim();
  }

  window.addEventListener("hashchange", route);

  // ---------- Theme ----------

  var THEME_KEY = "giacomo-dashboard-theme";

  function applyTheme(theme) {
    if (theme === "auto") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", theme);
    }
    document.getElementById("theme-label").textContent =
      theme === "auto" ? "Auto theme" : theme === "dark" ? "Dark theme" : "Light theme";
    applyThemeToDiagrams();
    if (simStaticState.cy) simStaticState.cy.style(buildSimCytoscapeStyle()).update();
  }

  function applyThemeToDiagrams() {
    if (!diagramsFrame || !diagramsFrame.contentDocument) return;
    var theme = localStorage.getItem(THEME_KEY) || "auto";
    var root = diagramsFrame.contentDocument.documentElement;
    if (theme === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
  }

  document.getElementById("theme-toggle").addEventListener("click", function () {
    var current = localStorage.getItem(THEME_KEY) || "auto";
    var next = current === "auto" ? "light" : current === "light" ? "dark" : "auto";
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });

  // ---------- Mobile nav ----------

  var shell = document.getElementById("shell");
  var navToggle = document.getElementById("nav-toggle");
  var navBackdrop = document.getElementById("nav-backdrop");

  function openMobileNav() {
    shell.classList.add("nav-open");
    navBackdrop.hidden = false;
    navToggle.setAttribute("aria-expanded", "true");
  }
  function closeMobileNav() {
    shell.classList.remove("nav-open");
    navBackdrop.hidden = true;
    navToggle.setAttribute("aria-expanded", "false");
  }
  navToggle.addEventListener("click", function () {
    shell.classList.contains("nav-open") ? closeMobileNav() : openMobileNav();
  });
  navBackdrop.addEventListener("click", closeMobileNav);

  // ---------- Init ----------

  buildNav();
  applyTheme(localStorage.getItem(THEME_KEY) || "auto");
  route();
})();

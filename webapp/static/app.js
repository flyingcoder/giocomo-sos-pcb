(function () {
  "use strict";

  var navData = JSON.parse(document.getElementById("nav-data").textContent);
  var content = document.getElementById("content");
  var navEl = document.getElementById("nav");

  var GROUP_ORDER = ["Overview", "Analysis", "Diagrams", "Source Data", "Screenshots", "Simulation"];

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
    fetch("/api/doc/" + key).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      currentDocSource = data.source;
      var meta = "<span>SOURCE: <b>" + escapeHtml(data.source) + "</b></span>" +
        '<span><a href="/raw/doc/' + key + '" target="_blank" rel="noopener">view raw markdown ↗</a></span>';
      setContent(sheetShell("MD", "md", meta, '<div class="doc">' + data.html + "</div>"));
    }).catch(function (err) {
      setContent('<div class="empty">Could not load this document (' + escapeHtml(err.message) + ").</div>");
    });
  }

  function renderJson(key) {
    setContent('<div class="empty">Loading + pretty-printing JSON…</div>');
    fetch("/api/json/" + key).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      var meta = "<span>SOURCE: <b>" + escapeHtml(data.source) + "</b></span>" +
        "<span>SIZE: <b>" + data.size.toLocaleString() + " B</b></span>" +
        '<span><a href="/raw/json/' + key + '" target="_blank" rel="noopener">open raw file ↗</a></span>';
      var body = '<p style="color:var(--ink-soft); margin-top:0;">' + escapeHtml(data.note) + "</p>" +
        '<pre class="json-pre">' + highlightJson(data.pretty) + "</pre>";
      setContent(sheetShell("JSON", "json", meta, body));
    }).catch(function (err) {
      setContent('<div class="empty">Could not load this file (' + escapeHtml(err.message) + ").</div>");
    });
  }

  function renderImg(key, title) {
    var meta = "<span>FILE: <b>" + escapeHtml(title) + "</b></span>" +
      '<span><a href="/image/' + key + '" target="_blank" rel="noopener">open full size ↗</a></span>';
    var body = '<div class="img-frame"><img src="/image/' + key + '" alt="' + escapeHtml(title) + '"></div>';
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

  // ---------- Router ----------

  function route() {
    var hash = location.hash.replace(/^#/, "") || "doc:overview";
    var item = itemsByRoute[hash];
    if (!item) {
      hash = "doc:overview";
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

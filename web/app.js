(() => {
  "use strict";

  const stage = document.getElementById("stage");
  const dispatchIdEl = document.getElementById("dispatchId");
  const themeToggle = document.getElementById("themeToggle");

  const STAGES = [
    "assignment",
    "brief-review",
    "wire-feed",
    "manuscript",
    "copy-desk",
    "final-review",
    "filed",
  ];

  const state = {
    threadId: null,
    topic: "",
    plan: [],
    revisionCount: 0,
    es: null,
  };

  // ------------------------------------------------------------------
  // Theme
  // ------------------------------------------------------------------

  function applyStoredTheme() {
    const saved = localStorage.getItem("wiredesk-theme");
    if (saved === "light" || saved === "dark") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const effective = current || (prefersDark ? "dark" : "light");
    const next = effective === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("wiredesk-theme", next);
  }

  applyStoredTheme();
  themeToggle.addEventListener("click", toggleTheme);

  // ------------------------------------------------------------------
  // Rail
  // ------------------------------------------------------------------

  function setRail(stageKey, status) {
    const idx = STAGES.indexOf(stageKey);
    STAGES.forEach((s, i) => {
      const el = document.querySelector(`.rail-step[data-stage="${s}"]`);
      if (!el) return;
      if (i < idx) el.dataset.status = "done";
      else if (i === idx) el.dataset.status = status;
      else el.dataset.status = "pending";
    });
  }

  // ------------------------------------------------------------------
  // Small markdown renderer, tuned for the writer agent's report format
  // (headers, paragraphs, bullet lists, [text](url) links, bare URLs,
  // and [n] citation markers).
  // ------------------------------------------------------------------

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function inlineMd(raw) {
    let out = escapeHtml(raw);
    out = out.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
    out = out.replace(/\[(\d+)\]/g, '<sup class="cite">[$1]</sup>');
    out = out.replace(
      /(^|[^"'>])(https?:\/\/[^\s<]+)/g,
      '$1<a href="$2" target="_blank" rel="noopener">$2</a>'
    );
    return out;
  }

  function mdToHtml(md) {
    const lines = (md || "").split(/\r?\n/);
    let html = "";
    let inList = false;
    let paraBuf = [];

    const flushPara = () => {
      if (paraBuf.length) {
        html += `<p>${inlineMd(paraBuf.join(" "))}</p>`;
        paraBuf = [];
      }
    };
    const closeList = () => {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
    };

    for (const raw of lines) {
      const line = raw.trim();
      if (line === "") {
        flushPara();
        closeList();
        continue;
      }
      const h = line.match(/^(#{1,3})\s+(.*)/);
      if (h) {
        flushPara();
        closeList();
        const level = h[1].length === 1 ? 1 : 2;
        html += `<h${level}>${inlineMd(h[2])}</h${level}>`;
        continue;
      }
      const li = line.match(/^[-*]\s+(.*)/);
      if (li) {
        flushPara();
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += `<li>${inlineMd(li[1])}</li>`;
        continue;
      }
      closeList();
      paraBuf.push(line);
    }
    flushPara();
    closeList();
    return html;

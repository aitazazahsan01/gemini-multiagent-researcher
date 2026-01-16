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
  }

  // ------------------------------------------------------------------
  // Panels
  // ------------------------------------------------------------------

  function renderBrief() {
    setRail("assignment", "active");
    dispatchIdEl.textContent = "";
    stage.innerHTML = `
      <div class="panel">
        <div class="panel-eyebrow">New assignment</div>
        <h1>What should the desk look into?</h1>
        <p class="lede">A planner agent will scope it into sub-questions, a researcher will wire out
          for sources, a writer will draft the report, and a critic will push back before anything
          gets filed. You'll sign off twice along the way.</p>
        <div class="card">
          <form id="briefForm">
            <div class="field">
              <label for="topicInput">Assignment topic</label>
              <textarea id="topicInput" rows="3" placeholder="e.g. The environmental impact of lithium-ion battery recycling" required minlength="3" maxlength="300"></textarea>
            </div>
            <div class="actions">
              <button type="submit" class="btn btn-primary">Open assignment</button>
            </div>
          </form>
        </div>
      </div>
    `;
    document.getElementById("briefForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const topic = document.getElementById("topicInput").value.trim();
      if (topic.length < 3) return;
      startAssignment(topic);
    });
    document.getElementById("topicInput").focus();
  }

  function renderWorking(eyebrow, title, lede, extraHtml) {
    stage.innerHTML = `
      <div class="panel">
        <div class="panel-eyebrow">${eyebrow}</div>
        <h1>${title}</h1>
        ${lede ? `<p class="lede">${lede}</p>` : ""}
        <div class="working">
          <span class="dot-flicker"><span></span><span></span><span></span></span>
          <span>Working…</span>
        </div>
        ${extraHtml || ""}
      </div>
    `;
  }

  function renderWireFeedWorking(plan, doneSet) {
    doneSet = doneSet || new Set();
    const items = plan
      .map((q, i) => {
        const isDone = doneSet.has(i);
        return `<li data-status="${isDone ? "done" : "pending"}">
          <span class="glyph">${isDone ? "✓" : "·"}</span>
          <span>${escapeHtml(q)}</span>
        </li>`;
      })
      .join("");
    renderWorking(
      "Wire feed",
      "Correspondents are on the wire",
      "Each sub-question gets its own search pass, summarized with inline citations.",
      `<ul class="feed-log">${items}</ul>`
    );
  }

  function renderPlanReview(payload) {
    setRail("brief-review", "waiting");
    state.plan = payload.plan;
    state.topic = payload.topic;
    const items = payload.plan
      .map((q) => `<li>${escapeHtml(q)}</li>`)
      .join("");
    stage.innerHTML = `
      <div class="panel">
        <div class="panel-eyebrow">Brief review · awaiting you</div>
        <h1>Does this brief cover the assignment?</h1>
        <p class="lede">${escapeHtml(payload.topic)}</p>
        <div class="card">
          <ol class="question-list">${items}</ol>
        </div>
        <div class="card" id="editCard" style="display:none;">
          <div class="field">
            <label for="editPlan">Replace the brief (one sub-question per line)</label>
            <textarea id="editPlan" rows="5">${payload.plan.join("\n")}</textarea>
          </div>
        </div>
        <div class="actions">
          <button class="btn btn-primary" id="approvePlan">Approve brief</button>
          <button class="btn btn-ghost" id="editPlanToggle">Rewrite brief</button>
          <button class="btn btn-primary" id="submitPlan" style="display:none;">Send rewritten brief</button>
        </div>
      </div>
    `;
    document.getElementById("approvePlan").addEventListener("click", () => resumeAssignment("approve"));
    document.getElementById("editPlanToggle").addEventListener("click", () => {
      document.getElementById("editCard").style.display = "block";
      document.getElementById("editPlanToggle").style.display = "none";
      document.getElementById("submitPlan").style.display = "inline-block";
    });
    document.getElementById("submitPlan").addEventListener("click", () => {
      const lines = document
        .getElementById("editPlan")
        .value.split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
      resumeAssignment(lines.join("; "));
    });
  }

  function renderManuscriptWorking(reason) {
    setRail("manuscript", "active");
    const title = state.revisionCount > 0 ? `Redrafting — draft no. ${state.revisionCount + 1}` : "The draft desk is composing";
    renderWorking("Manuscript", title, reason || "Synthesizing the wire feed into a cited report.");
  }

  function renderCopyDeskWorking() {
    setRail("copy-desk", "active");
    renderWorking("Copy desk", "Under the red pen", "Checking the draft against the wire feed for accuracy, coverage, and citations.");
  }

  function renderFinalReview(payload) {
    setRail("final-review", "waiting");
    const verdictPill =
      payload.critic_verdict === "approved"
        ? `<span class="pill pill-success">Copy desk: approved</span>`
        : `<span class="pill pill-critical">Copy desk: revision cap reached</span>`;
    const critiqueBlock = payload.critic_feedback
      ? `<div class="critique-note"><strong>Copy desk notes:</strong> ${escapeHtml(payload.critic_feedback)}</div>`
      : "";
    stage.innerHTML = `
      <div class="panel" style="max-width:820px;">
        <div class="panel-eyebrow">Final review · awaiting you</div>
        <h1>Ready to file?</h1>
        <div style="margin-bottom:1rem;">${verdictPill} <span class="revision-badge">draft no. ${state.revisionCount + 1}</span></div>
        ${critiqueBlock}
        <div class="manuscript-wrap">
          <div class="manuscript">${mdToHtml(payload.draft)}</div>
        </div>
        <div class="card">
          <div class="field">
            <label for="finalFeedback">Feedback for another pass (optional — leave blank to file as-is)</label>
            <textarea id="finalFeedback" rows="3" placeholder="e.g. expand the section on regulatory frameworks"></textarea>
          </div>
        </div>
        <div class="actions">
          <button class="btn btn-primary" id="approveFinal">File report</button>
          <button class="btn btn-ghost" id="sendFeedback">Send back for another pass</button>
        </div>
      </div>
    `;
    document.getElementById("approveFinal").addEventListener("click", () => resumeAssignment("approve"));
    document.getElementById("sendFeedback").addEventListener("click", () => {
      const fb = document.getElementById("finalFeedback").value.trim();
      if (!fb) return;
      resumeAssignment(fb);
    });
  }

  function renderFiled(finalState) {
    setRail("filed", "done");
    const blob = new Blob([finalState.draft], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    stage.innerHTML = `
      <div class="panel" style="max-width:820px;">
        <div class="panel-eyebrow">Filed</div>
        <h1>Report filed</h1>
        <div class="filed-note">Approved after ${finalState.revision_count} revision${finalState.revision_count === 1 ? "" : "s"}.</div>
        <div class="manuscript-wrap">
          <div class="manuscript">${mdToHtml(finalState.draft)}</div>
        </div>
        <div class="actions">
          <a class="btn btn-primary" href="${url}" download="report.md">Download manuscript (.md)</a>
          <button class="btn btn-ghost" id="newAssignment">Start a new assignment</button>
        </div>
      </div>
    `;
    document.getElementById("newAssignment").addEventListener("click", () => {
      state.revisionCount = 0;
      state.threadId = null;
      renderBrief();
    });
  }

  function renderError(message) {
    stage.innerHTML = `
      <div class="panel">
        <div class="panel-eyebrow">Wire down</div>
        <h1>Something b
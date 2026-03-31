/* ============================================================
   Agile Wargame Simulator — Dashboard JS
   Vanilla ES2020, no frameworks, no npm
   ============================================================ */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const AGENTS = [
  "developer", "qa_engineer", "tech_lead", "product_owner",
  "security_architect", "cloud_engineer", "scrum_master", "software_architect",
];

const state = {
  simId:             null,
  es:                null,   // EventSource
  reports:           {},     // sprint_num -> report dict
  activeReportSprint:null,
  activeTab:         "log",  // "log" | "graph"
  agentFilter:       null,   // agentId string | null
};

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
let elProvider, elScenario, elSprints, elRunBtn;
let elStatusBadge, elCurrentSprint;
let elGaugeFill, elGaugeVal;
let elLogTbody;
let elReportTabs, elReportContent;
let elTabLog, elTabGraph, elPanelLog, elPanelGraph;

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  elProvider      = document.getElementById("sel-provider");
  elScenario      = document.getElementById("sel-scenario");
  elSprints       = document.getElementById("inp-sprints");
  elRunBtn        = document.getElementById("btn-run");
  elStatusBadge   = document.getElementById("status-badge");
  elCurrentSprint = document.getElementById("current-sprint");
  elGaugeFill     = document.getElementById("gauge-fill");
  elGaugeVal      = document.getElementById("gauge-val");
  elLogTbody      = document.getElementById("log-tbody");
  elReportTabs    = document.getElementById("report-tabs");
  elReportContent = document.getElementById("report-content");
  elTabLog        = document.getElementById("tab-log");
  elTabGraph      = document.getElementById("tab-graph");
  elPanelLog      = document.getElementById("panel-log");
  elPanelGraph    = document.getElementById("panel-graph");

  elRunBtn.addEventListener("click", onRun);

  // Tab switching
  elTabLog.addEventListener("click",   () => switchTab("log"));
  elTabGraph.addEventListener("click", () => switchTab("graph"));

  // Init D3 graph module
  const graphContainer = document.getElementById("graph-container");
  const tooltip        = document.getElementById("graph-tooltip");
  if (window.GraphModule) {
    GraphModule.init(graphContainer, tooltip, filterLogByAgent);
  }

  await loadScenarios();
  buildAgentCards();
  setStatus("idle");
});

// ---------------------------------------------------------------------------
// Tab management
// ---------------------------------------------------------------------------
function switchTab(name) {
  state.activeTab = name;

  elTabLog.classList.toggle("active",   name === "log");
  elTabGraph.classList.toggle("active", name === "graph");
  elPanelLog.style.display   = name === "log"   ? "" : "none";
  elPanelGraph.style.display = name === "graph" ? "" : "none";

  if (name === "graph" && state.simId && window.GraphModule) {
    GraphModule.refresh(state.simId);
  }
}

// ---------------------------------------------------------------------------
// Log filter (called by GraphModule on node click)
// ---------------------------------------------------------------------------
function filterLogByAgent(agentId) {
  state.agentFilter = agentId;
  const rows = elLogTbody.querySelectorAll("tr");
  rows.forEach(tr => {
    if (!agentId) {
      tr.style.display = "";
      return;
    }
    const cell = tr.querySelector(".col-agent");
    tr.style.display = (cell && cell.textContent === agentId) ? "" : "none";
  });
}

// ---------------------------------------------------------------------------
// Scenarios
// ---------------------------------------------------------------------------
async function loadScenarios() {
  try {
    const data = await fetchJSON("/scenarios");
    elScenario.innerHTML = "";
    data.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.path;
      opt.textContent = `${s.name} (${s.story_count} stories)`;
      elScenario.appendChild(opt);
    });
  } catch (_) {
    // seeds/ not found — keep default
  }
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------
async function onRun() {
  if (state.es) {
    state.es.close();
    state.es = null;
  }

  // Reset UI
  elLogTbody.innerHTML = "";
  elReportTabs.innerHTML = "";
  elReportContent.innerHTML = '<p class="empty-state">Waiting for sprint reports…</p>';
  state.reports = {};
  state.activeReportSprint = null;
  state.agentFilter = null;
  resetGauge();
  resetAgentCards();

  if (window.GraphModule) GraphModule.reset();

  elRunBtn.disabled = true;
  setStatus("running");

  const body = {
    provider: elProvider.value,
    scenario: elScenario.value || "seeds/etp",
    sprints:  parseInt(elSprints.value, 10) || 2,
  };

  let simId;
  try {
    const res = await fetchJSON("/simulate", { method: "POST", body: JSON.stringify(body) });
    simId = res.sim_id;
    state.simId = simId;
  } catch (err) {
    setStatus("error");
    elRunBtn.disabled = false;
    appendErrorRow(`Failed to start simulation: ${err.message}`);
    return;
  }

  openStream(simId);
}

// ---------------------------------------------------------------------------
// SSE stream
// ---------------------------------------------------------------------------
function openStream(simId) {
  const es = new EventSource(`/simulate/${simId}/stream`);
  state.es = es;

  es.addEventListener("turn",                onTurnEvent);
  es.addEventListener("sprint_complete",     onSprintComplete);
  es.addEventListener("simulation_complete", onSimulationComplete);
  es.addEventListener("error",               onErrorEvent);
  es.addEventListener("heartbeat",           () => {});

  es.onerror = () => {
    if (elStatusBadge.dataset.status === "running") {
      setStatus("error");
      appendErrorRow("SSE connection lost.");
    }
    es.close();
    elRunBtn.disabled = false;
  };
}

// ---------------------------------------------------------------------------
// SSE event handlers
// ---------------------------------------------------------------------------
function onTurnEvent(e) {
  const d = JSON.parse(e.data);
  elCurrentSprint.textContent = `Sprint ${d.sprint} / ${d.total_sprints}  —  Turn ${d.turn}`;

  d.responses.forEach(r => {
    appendTurnRow(d.sprint, d.turn, r);
    updateAgentCard(r);
  });

  // Re-apply log filter if one is active
  if (state.agentFilter) filterLogByAgent(state.agentFilter);

  // Update graph in real time
  if (window.GraphModule) GraphModule.onTurnData(d.responses);
}

function onSprintComplete(e) {
  const report = JSON.parse(e.data);
  state.reports[report.sprint] = report;
  addReportTab(report.sprint);
  updateGauge(report.friction_index);

  // Refresh graph with server-side data after each sprint
  if (window.GraphModule && state.simId) GraphModule.refresh(state.simId);
}

function onSimulationComplete(e) {
  setStatus("done");
  elRunBtn.disabled = false;
  state.es.close();
  state.es = null;
  elCurrentSprint.textContent = "Simulation complete";

  // Final graph refresh
  if (window.GraphModule && state.simId) GraphModule.refresh(state.simId);
}

function onErrorEvent(e) {
  const d = JSON.parse(e.data);
  setStatus("error");
  appendErrorRow(d.message || "Unknown error");
  elRunBtn.disabled = false;
}

// ---------------------------------------------------------------------------
// Turn log
// ---------------------------------------------------------------------------
function appendTurnRow(sprint, turn, r) {
  const tr = document.createElement("tr");
  const rationale = r.rationale.length > 90
    ? r.rationale.slice(0, 90) + "…"
    : r.rationale;

  tr.innerHTML = `
    <td class="col-sprint">${sprint}</td>
    <td class="col-turn">${turn}</td>
    <td class="col-agent">${r.agent_id}</td>
    <td class="col-action"><span class="action-${r.action}">${r.action}</span></td>
    <td class="col-conf">${r.confidence.toFixed(2)}</td>
    <td class="col-rat" title="${escapeHtml(r.rationale)}">${escapeHtml(rationale)}</td>
  `;
  elLogTbody.prepend(tr);
}

function appendErrorRow(msg) {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td colspan="6" style="color:var(--red);padding:8px 10px;">[ERROR] ${escapeHtml(msg)}</td>`;
  elLogTbody.prepend(tr);
}

// ---------------------------------------------------------------------------
// Agent cards
// ---------------------------------------------------------------------------
function buildAgentCards() {
  const grid = document.getElementById("agent-grid");
  grid.innerHTML = "";
  AGENTS.forEach(role => {
    const card = document.createElement("div");
    card.className = "agent-card";
    card.id = `card-${role}`;
    card.innerHTML = `
      <div class="agent-name">${formatRole(role)}</div>
      <div class="agent-action" id="act-${role}">—</div>
      <div class="agent-conf"  id="conf-${role}"></div>
    `;
    grid.appendChild(card);
  });
}

function updateAgentCard(r) {
  const card = document.getElementById(`card-${r.agent_id}`);
  if (!card) return;
  card.className = `agent-card card-${r.action}`;
  document.getElementById(`act-${r.agent_id}`).innerHTML =
    `<span class="action-${r.action}">${r.action}</span>`;
  document.getElementById(`conf-${r.agent_id}`).textContent =
    `conf ${r.confidence.toFixed(2)}${r.tech_debt_added ? ` | debt +${r.tech_debt_added}` : ""}`;
}

function resetAgentCards() {
  AGENTS.forEach(role => {
    const card = document.getElementById(`card-${role}`);
    if (!card) return;
    card.className = "agent-card";
    document.getElementById(`act-${role}`).textContent = "—";
    document.getElementById(`conf-${role}`).textContent = "";
  });
}

// ---------------------------------------------------------------------------
// Friction gauge
// ---------------------------------------------------------------------------
function updateGauge(fi) {
  const pct = Math.round(fi * 100);
  elGaugeFill.style.width = `${pct}%`;
  elGaugeVal.textContent  = pct;

  if (fi < 0.33)      elGaugeFill.style.backgroundColor = "var(--green)";
  else if (fi < 0.66) elGaugeFill.style.backgroundColor = "var(--yellow)";
  else                elGaugeFill.style.backgroundColor = "var(--red)";
}

function resetGauge() {
  elGaugeFill.style.width = "0%";
  elGaugeFill.style.backgroundColor = "var(--green)";
  elGaugeVal.textContent = "0";
}

// ---------------------------------------------------------------------------
// God Agent report panel
// ---------------------------------------------------------------------------
function addReportTab(sprint) {
  const tab = document.createElement("button");
  tab.className = "sprint-tab";
  tab.textContent = `S${sprint}`;
  tab.dataset.sprint = sprint;
  tab.addEventListener("click", () => showReport(sprint));
  elReportTabs.appendChild(tab);
  showReport(sprint);
}

function showReport(sprint) {
  elReportTabs.querySelectorAll(".sprint-tab").forEach(t => {
    t.classList.toggle("active", parseInt(t.dataset.sprint, 10) === sprint);
  });

  state.activeReportSprint = sprint;
  const report = state.reports[sprint];
  if (!report) { elReportContent.innerHTML = '<p class="empty-state">No data yet.</p>'; return; }

  const confPct = Math.round(report.confidence_score * 100);
  const reliableLabel = report.is_reliable
    ? '<span style="color:var(--green)">RELIABLE</span>'
    : '<span style="color:var(--yellow)">LOW CONFIDENCE</span>';

  let html = `
    <div class="report-section">
      <h3>Sprint ${sprint} Summary</h3>
      <div class="report-meta">
        <div class="meta-item"><span class="meta-key">Velocity </span><span class="meta-val">${report.velocity} pts</span></div>
        <div class="meta-item"><span class="meta-key">Decay </span><span class="meta-val">${report.velocity_decay_pct > 0 ? "+" : ""}${report.velocity_decay_pct}%</span></div>
        <div class="meta-item"><span class="meta-key">Tech Debt </span><span class="meta-val">+${report.tech_debt_delta}</span></div>
        <div class="meta-item"><span class="meta-key">Friction </span><span class="meta-val">${(report.friction_index * 100).toFixed(0)}%</span></div>
        <div class="meta-item"><span class="meta-key">Confidence </span><span class="meta-val">${confPct}%</span></div>
        <div class="meta-item">${reliableLabel}</div>
      </div>
    </div>
  `;

  if (report.predicted_risks && report.predicted_risks.length > 0) {
    html += `<div class="report-section"><h3>Predicted Risks</h3>`;
    report.predicted_risks.forEach(r => {
      html += `
        <div class="risk-card ${r.severity}">
          <div class="risk-header">
            <span class="risk-id">${r.id}</span>
            <span class="sev-${r.severity}">${r.severity}</span>
          </div>
          <div class="risk-desc">${escapeHtml(r.description)}</div>
          <div class="risk-rec">${escapeHtml(r.recommendation)}</div>
        </div>
      `;
    });
    html += `</div>`;
  }

  if (report.recommendations && report.recommendations.length > 0) {
    html += `<div class="report-section"><h3>Recommendations</h3><ul class="rec-list">`;
    report.recommendations.forEach(rec => {
      html += `<li>${escapeHtml(rec)}</li>`;
    });
    html += `</ul></div>`;
  }

  if (report.friction_hotspots && report.friction_hotspots.length > 0) {
    html += `<div class="report-section"><h3>Friction Hotspots</h3>`;
    report.friction_hotspots.forEach(h => {
      const pair = Array.isArray(h.agent_pair) ? h.agent_pair.join(" vs ") : String(h.agent_pair);
      html += `<div class="risk-card MEDIUM" style="margin-bottom:6px;">
        <div style="font-weight:bold;font-size:11px;">${escapeHtml(pair)}</div>
        <div style="font-size:10px;color:var(--muted);">${h.conflict_count} conflicts — ${escapeHtml(h.root_cause)}</div>
      </div>`;
    });
    html += `</div>`;
  }

  elReportContent.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------
function setStatus(s) {
  elStatusBadge.className = `status-${s}`;
  elStatusBadge.dataset.status = s;
  const labels = { idle: "IDLE", running: "RUNNING", done: "DONE", error: "ERROR" };
  elStatusBadge.innerHTML = s === "running"
    ? `<span class="running-dot"></span>${labels[s]}`
    : labels[s] || s.toUpperCase();
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
async function fetchJSON(url, opts = {}) {
  const defaults = { headers: { "Content-Type": "application/json" } };
  const res = await fetch(url, { ...defaults, ...opts });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatRole(role) {
  return role.replace(/_/g, " ");
}

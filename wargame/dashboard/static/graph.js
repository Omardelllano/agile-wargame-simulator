/* ============================================================
   Agile Wargame Simulator — Agent Force Graph  (D3 v7)
   Exposes: window.GraphModule
   ============================================================ */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Visual constants
  // ---------------------------------------------------------------------------
  const R_MIN = 20;
  const R_MAX = 45;

  const NODE_COLORS = {
    COMPLETE:     "#1D9E75",
    APPROVE:      "#378ADD",
    REPRIORITIZE: "#378ADD",
    ESCALATE:     "#EF9F27",
    IMPEDIMENT:   "#EF9F27",
    FLAG:         "#D85A30",
    VETO:         "#E24B4A",
    BLOCK_DONE:   "#E24B4A",
    IDLE:         "#888780",
  };

  // Per-action friction weights (mirrors Python side)
  const FRICTION_WEIGHTS = {
    VETO: 1.0, BLOCK_DONE: 0.9, FLAG: 0.8,
    IMPEDIMENT: 0.7, ESCALATE: 0.5, REPRIORITIZE: 0.4,
  };

  const KNOWN_PAIRS = [
    ["tech_lead",         "product_owner"],
    ["qa_engineer",       "developer"],
    ["security_architect","cloud_engineer"],
    ["software_architect","developer"],
  ];
  const KNOWN_MULTIPLIER = 2.0;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function isKnownPair(a, b) {
    return KNOWN_PAIRS.some(([x, y]) => (x===a&&y===b)||(x===b&&y===a));
  }

  function nodeColor(action) {
    return NODE_COLORS[action] || "#888780";
  }

  function nodeR(actions) {
    const c = Math.max(1, Math.min(actions || 1, 60));
    return R_MIN + (R_MAX - R_MIN) * ((c - 1) / 59);
  }

  function edgeW(interactions) {
    const c = Math.max(1, Math.min(interactions || 1, 20));
    return 1 + 7 * ((c - 1) / 19);
  }

  function frictionColor(f) {
    if (f < 0.3) return "#1D9E75";
    if (f < 0.6) return "#EF9F27";
    return "#E24B4A";
  }

  function arrowId(color) {
    return "arr-" + color.replace("#", "");
  }

  async function _get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  // ---------------------------------------------------------------------------
  // Module-level state
  // ---------------------------------------------------------------------------
  let _container = null;
  let _tooltip   = null;
  let _onFilter  = null;   // callback(agentId|null)

  let _svg = null;
  let _g   = null;         // zoom group
  let _sim = null;

  let _linkSel = null;
  let _nodeSel = null;

  let _currentSimId = null;
  let _data = { nodes: [], links: [] };

  // Real-time incremental counters
  const _rt = {
    actions:  {},   // {agent: count}
    fw:       {},   // {agent: friction-weight-sum}
    last:     {},   // {agent: last-action}
  };

  let _activeNode = null;   // node ID currently filtered
  let _dashTick = false;    // dash animation flag

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  window.GraphModule = {

    init(containerEl, tooltipEl, filterCb) {
      _container = containerEl;
      _tooltip   = tooltipEl;
      _onFilter  = filterCb;
      _buildSvg();
    },

    async refresh(simId) {
      if (!simId || !_svg) return;
      _currentSimId = simId;

      // Update force center to current container size
      const w = _container.clientWidth  || 600;
      const h = _container.clientHeight || 400;
      _sim.force("center", d3.forceCenter(w / 2, h / 2));

      try {
        const data = await _get("/graph/" + simId);
        _mergeRtIntoData(data);
        _data = data;
        _render(data);
      } catch (_) { /* no data yet — ignore */ }
    },

    onTurnData(responses) {
      responses.forEach(r => {
        const a = r.agent_id;
        _rt.actions[a] = (_rt.actions[a] || 0) + 1;
        _rt.fw[a]      = (_rt.fw[a]      || 0) + (FRICTION_WEIGHTS[r.action] || 0);
        _rt.last[a]    = r.action;
      });

      if (!_nodeSel) return;

      // Update node colours + pulse
      const updated = new Set(responses.map(r => r.agent_id));
      _nodeSel
        .filter(d => updated.has(d.id))
        .select("circle")
        .attr("fill", d => nodeColor(_rt.last[d.id] || d.last_action))
        .interrupt()
        .transition().duration(180).attr("r", d => nodeR(_rt.actions[d.id] || d.actions) * 1.4)
        .transition().duration(280).attr("r", d => nodeR(_rt.actions[d.id] || d.actions));

      // Recolor edges live (no layout change)
      if (_linkSel) {
        _linkSel.each(function(d) {
          const sId = d.source.id || d.source;
          const tId = d.target.id || d.target;
          const cA  = _rt.actions[sId] || 1;
          const cB  = _rt.actions[tId] || 1;
          const fwA = _rt.fw[sId] || 0;
          const fwB = _rt.fw[tId] || 0;
          let f = (fwA + fwB) / (cA + cB);
          if (isKnownPair(sId, tId)) f = Math.min(f * KNOWN_MULTIPLIER, 1.0);
          d._rtFriction = f;
          d3.select(this)
            .attr("stroke",           frictionColor(f))
            .attr("stroke-dasharray", f >= 0.6 ? "7 3" : null)
            .attr("marker-end",       "url(#" + arrowId(frictionColor(f)) + ")");
        });
      }
    },

    reset() {
      Object.keys(_rt).forEach(k => { _rt[k] = {}; });
      _currentSimId = null;
      _data = { nodes: [], links: [] };
      _activeNode = null;
      if (_g) {
        _g.selectAll(".glink").remove();
        _g.selectAll(".gnode").remove();
      }
      _linkSel = null;
      _nodeSel = null;
    },
  };

  // ---------------------------------------------------------------------------
  // SVG bootstrap (called once)
  // ---------------------------------------------------------------------------
  function _buildSvg() {
    _svg = d3.select(_container)
      .append("svg")
      .attr("width",  "100%")
      .attr("height", "100%")
      .style("display", "block");

    // Arrow markers for each colour
    const defs = _svg.append("defs");
    ["#1D9E75", "#EF9F27", "#E24B4A", "#888780"].forEach(col => {
      defs.append("marker")
        .attr("id",          arrowId(col))
        .attr("viewBox",     "0 -5 10 10")
        .attr("refX",        15)
        .attr("refY",        0)
        .attr("markerWidth", 6)
        .attr("markerHeight",6)
        .attr("orient",      "auto")
        .append("path")
        .attr("d",    "M0,-5L10,0L0,5")
        .attr("fill", col)
        .attr("opacity", 0.85);
    });

    // Zoom behaviour
    const zoom = d3.zoom()
      .scaleExtent([0.25, 4])
      .on("zoom", e => _g.attr("transform", e.transform));
    _svg.call(zoom);

    // Main group
    _g = _svg.append("g").attr("class", "graph-root");

    // Force simulation (placeholder, updated in refresh)
    _sim = d3.forceSimulation()
      .force("link",      d3.forceLink().id(d => d.id).distance(150).strength(0.55))
      .force("charge",    d3.forceManyBody().strength(-480))
      .force("center",    d3.forceCenter(300, 200))
      .force("collision", d3.forceCollide().radius(R_MAX + 14));

    // Legend
    _buildLegend();

    // Dismiss filter on SVG background click
    _svg.on("click", () => {
      if (_activeNode) {
        _activeNode = null;
        if (_nodeSel) _nodeSel.select("circle").attr("opacity", 1).attr("stroke-width", 1.5);
        if (_linkSel) _linkSel.attr("opacity", 0.75);
        if (_onFilter) _onFilter(null);
      }
    });

    // Start dash animation loop once
    _startDash();
  }

  // ---------------------------------------------------------------------------
  // Full render pass
  // ---------------------------------------------------------------------------
  function _render(data) {
    if (!_g) return;

    // -- Links --
    _linkSel = _g.selectAll(".glink")
      .data(data.links, d => d.source + "~" + d.target)
      .join(
        enter => enter.append("line").attr("class", "glink").attr("opacity", 0.75),
        update => update,
        exit => exit.remove()
      )
      .attr("stroke",           d => frictionColor(d.friction))
      .attr("stroke-width",     d => edgeW(d.interactions))
      .attr("stroke-dasharray", d => d.friction >= 0.6 ? "7 3" : null)
      .attr("marker-end",       d => "url(#" + arrowId(frictionColor(d.friction)) + ")")
      .on("mouseover", _edgeOver)
      .on("mousemove", _edgeMove)
      .on("mouseout",  _edgeOut);

    // -- Nodes --
    _nodeSel = _g.selectAll(".gnode")
      .data(data.nodes, d => d.id)
      .join(
        enter => {
          const grp = enter.append("g")
            .attr("class", "gnode")
            .attr("cursor", "pointer")
            .call(
              d3.drag()
                .on("start", (ev, d) => { if (!ev.active) _sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
                .on("drag",  (ev, d) => { d.fx=ev.x; d.fy=ev.y; })
                .on("end",   (ev, d) => { if (!ev.active) _sim.alphaTarget(0); d.fx=null; d.fy=null; })
            )
            .on("click", _nodeClick);

          grp.append("circle")
            .attr("r",            d => nodeR(d.actions))
            .attr("fill",         d => nodeColor(d.last_action))
            .attr("stroke",       "#30363d")
            .attr("stroke-width", 1.5);

          grp.append("text")
            .attr("text-anchor",  "middle")
            .attr("dy",           d => nodeR(d.actions) + 13)
            .attr("font-size",    "10px")
            .attr("fill",         "#8b949e")
            .attr("pointer-events","none")
            .text(d => d.id.replace(/_/g, " "));

          return grp;
        },
        update => {
          update.select("circle")
            .attr("r",    d => nodeR(d.actions))
            .attr("fill", d => nodeColor(d.last_action));
          update.select("text")
            .attr("dy", d => nodeR(d.actions) + 13);
          return update;
        },
        exit => exit.remove()
      );

    // -- Simulation --
    _sim.nodes(data.nodes).on("tick", _tick);
    _sim.force("link").links(data.links);
    _sim.alpha(0.6).restart();
  }

  function _tick() {
    if (_linkSel) {
      _linkSel
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => _tipX(d))
        .attr("y2", d => _tipY(d));
    }
    if (_nodeSel) {
      _nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);
    }
  }

  // Arrow endpoint offset so head sits on circle rim, not centre
  function _tipX(d) {
    const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
    const dist = Math.hypot(dx, dy) || 1;
    return d.target.x - (dx / dist) * (nodeR(d.target.actions) + 3);
  }
  function _tipY(d) {
    const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
    const dist = Math.hypot(dx, dy) || 1;
    return d.target.y - (dy / dist) * (nodeR(d.target.actions) + 3);
  }

  // ---------------------------------------------------------------------------
  // Merge real-time counters into fetched data before rendering
  // ---------------------------------------------------------------------------
  function _mergeRtIntoData(data) {
    // Preserve existing node positions
    const posMap = {};
    if (_data.nodes.length) {
      _data.nodes.forEach(n => { posMap[n.id] = { x: n.x, y: n.y }; });
    }
    data.nodes.forEach(n => {
      if (posMap[n.id]) { n.x = posMap[n.id].x; n.y = posMap[n.id].y; }
      if (_rt.last[n.id])    n.last_action = _rt.last[n.id];
      if (_rt.actions[n.id]) n.actions     = _rt.actions[n.id];
    });
  }

  // ---------------------------------------------------------------------------
  // Node click → filter log table
  // ---------------------------------------------------------------------------
  function _nodeClick(event, d) {
    event.stopPropagation();
    if (_activeNode === d.id) {
      // Deselect
      _activeNode = null;
      _nodeSel.select("circle").attr("opacity", 1).attr("stroke-width", 1.5);
      _linkSel.attr("opacity", 0.75);
      if (_onFilter) _onFilter(null);
    } else {
      _activeNode = d.id;
      _nodeSel.select("circle")
        .attr("opacity",      n => n.id === d.id ? 1 : 0.25)
        .attr("stroke-width", n => n.id === d.id ? 2.5 : 1);
      _linkSel.attr("opacity", l => {
        const s = l.source.id || l.source;
        const t = l.target.id || l.target;
        return (s === d.id || t === d.id) ? 0.9 : 0.12;
      });
      if (_onFilter) _onFilter(d.id);
    }
  }

  // ---------------------------------------------------------------------------
  // Edge tooltip
  // ---------------------------------------------------------------------------
  function _edgeOver(event, d) {
    if (!_tooltip) return;
    const s = d.source.id || d.source;
    const t = d.target.id || d.target;
    const f = d._rtFriction !== undefined ? d._rtFriction : d.friction;
    const col = frictionColor(f);
    _tooltip.innerHTML =
      `<strong>${s}</strong> ↔ <strong>${t}</strong><br>` +
      `${d.interactions} interactions &nbsp;|&nbsp; ` +
      `friction: <span style="color:${col};font-weight:bold">${(f*100).toFixed(0)}%</span>`;
    _tooltip.style.display = "block";
    _edgeMove(event);
  }
  function _edgeMove(event) {
    if (!_tooltip) return;
    _tooltip.style.left = (event.pageX + 14) + "px";
    _tooltip.style.top  = (event.pageY - 32) + "px";
  }
  function _edgeOut() {
    if (_tooltip) _tooltip.style.display = "none";
  }

  // ---------------------------------------------------------------------------
  // Animated dash for high-friction edges
  // ---------------------------------------------------------------------------
  function _startDash() {
    if (_dashTick) return;
    _dashTick = true;
    let offset = 0;
    function step() {
      offset = (offset - 0.8) % 10;
      if (_linkSel) {
        _linkSel.filter("[stroke-dasharray]")
          .attr("stroke-dashoffset", offset);
      }
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ---------------------------------------------------------------------------
  // Legend (bottom-left of SVG)
  // ---------------------------------------------------------------------------
  function _buildLegend() {
    const lg = _svg.append("g")
      .attr("class", "graph-legend")
      .attr("transform", "translate(10,10)");

    // Background box
    lg.append("rect")
      .attr("x", -4).attr("y", -4)
      .attr("width", 178).attr("height", 202)
      .attr("rx", 4)
      .attr("fill", "#161b22").attr("opacity", 0.88);

    const nodeItems = [
      { color: "#1D9E75", label: "COMPLETE" },
      { color: "#378ADD", label: "APPROVE / REPRIORITIZE" },
      { color: "#EF9F27", label: "ESCALATE / IMPEDIMENT" },
      { color: "#D85A30", label: "FLAG" },
      { color: "#E24B4A", label: "VETO / BLOCK" },
      { color: "#888780", label: "IDLE" },
    ];

    lg.append("text").attr("x", 0).attr("y", 9)
      .attr("font-size","9px").attr("fill","#58a6ff")
      .attr("font-weight","bold").attr("letter-spacing","0.08em")
      .text("NODES");

    nodeItems.forEach((item, i) => {
      const y = 22 + i * 17;
      lg.append("circle").attr("cx", 6).attr("cy", y).attr("r", 5).attr("fill", item.color);
      lg.append("text").attr("x", 16).attr("y", y + 4)
        .attr("font-size","9px").attr("fill","#8b949e").text(item.label);
    });

    const ey = 22 + nodeItems.length * 17 + 8;
    lg.append("text").attr("x", 0).attr("y", ey)
      .attr("font-size","9px").attr("fill","#58a6ff")
      .attr("font-weight","bold").attr("letter-spacing","0.08em")
      .text("EDGES (friction)");

    [
      { color: "#1D9E75", label: "< 30%  low" },
      { color: "#EF9F27", label: "30–60%  medium" },
      { color: "#E24B4A", label: "≥ 60%  high  ~~~" },
    ].forEach((item, i) => {
      const y = ey + 12 + i * 16;
      lg.append("line").attr("x1",1).attr("y1",y).attr("x2",14).attr("y2",y)
        .attr("stroke",item.color).attr("stroke-width",2.5);
      lg.append("text").attr("x",18).attr("y",y+4)
        .attr("font-size","9px").attr("fill","#8b949e").text(item.label);
    });
  }

})();

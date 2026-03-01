import { app } from "../../scripts/app.js";

const BYPASS_MODE = 4;              // ComfyUI bypass
const ENABLE_MODE = LiteGraph.ALWAYS;

const CT_PARENT = "HYBS_GroupBypasser_Parent";
const CT_CHILD  = "HYBS_GroupBypasser_Child";
const CT_PANEL  = "HYBS_GroupBypasser_Panel";
const PANEL_SYNC_INTERVAL_MS = 250;

// ------------------------- graph helpers -------------------------
function getGroups(graph) {
  return (graph && graph._groups) ? graph._groups : [];
}

function getGroupTitle(group) {
  return (group && typeof group.title === "string") ? group.title : "Group";
}

function recomputeGroupNodes(group) {
  try {
    if (group && typeof group.recomputeInsideNodes === "function") {
      group.recomputeInsideNodes();
    }
  } catch (_) {}
  return group?._nodes ?? [];
}

// Collect Main + all subgraphs
function getAllGraphs(rootGraph) {
  const graphs = [];
  const visited = new Set();

  function walk(g) {
    if (!g || visited.has(g)) return;
    visited.add(g);
    graphs.push(g);

    const nodes = g._nodes || [];
    for (const n of nodes) {
      if (n && n.subgraph) walk(n.subgraph);
    }
  }

  walk(rootGraph);
  return graphs;
}

function getGraphLabel(graph) {
  // LiteGraph subgraph graph may have an owner node in _subgraph_node
  const owner = graph?._subgraph_node;
  if (owner && typeof owner.title === "string" && owner.title.trim()) return owner.title.trim();
  return "Main";
}

// ------------------------- bypass helpers (subgraph-aware) -------------------------
function setNodeBypassDeep(node, bypass) {
  if (!node) return;
  node.mode = bypass ? BYPASS_MODE : ENABLE_MODE;

  // If this node is a Subgraph node, also apply to its internal graph nodes recursively
  const sg = node.subgraph;
  if (sg && Array.isArray(sg._nodes)) {
    for (const inner of sg._nodes) {
      if (!inner) continue;
      setNodeBypassDeep(inner, bypass);
    }
  }
}

function setGroupBypass(group, bypass) {
  const nodes = recomputeGroupNodes(group);
  for (const node of nodes) {
    setNodeBypassDeep(node, bypass);
  }
}

function isGroupBypassed(group) {
  const nodes = recomputeGroupNodes(group);
  if (!nodes || !nodes.length) return false;
  return nodes.some((n) => n && n.mode === BYPASS_MODE);
}

function findGroupsContainingNode(graph, targetNode) {
  const groups = getGroups(graph);
  const hit = [];
  for (const g of groups) {
    const nodes = recomputeGroupNodes(g);
    if (nodes && nodes.includes(targetNode)) hit.push(g);
  }
  return hit;
}

function getParentNodesInGroup(graph, group) {
  const nodes = recomputeGroupNodes(group);
  if (!nodes || !nodes.length) return [];
  return nodes.filter((n) => n && n.comfyClass === CT_PARENT);
}

function groupHasParentNode(graph, group) {
  const nodes = recomputeGroupNodes(group);
  if (!nodes || !nodes.length) return false;
  return nodes.some((n) => n && n.comfyClass === CT_PARENT);
}

// ------------------------- link traversal (per-graph) -------------------------
function getLinkedNodesFromOutput(graph, node, outputIndex = 0) {
  const out = node.outputs?.[outputIndex];
  const linkIds = out?.links ?? [];
  const result = [];
  for (const linkId of linkIds) {
    const link = graph.links?.[linkId];
    if (!link) continue;
    const targetNode = graph.getNodeById?.(link.target_id);
    if (targetNode) result.push(targetNode);
  }
  return result;
}

function collectChildNodes(graph, parentNode) {
  const visited = new Set();
  const queue = [];

  // Parent output(0) -> Child input
  for (const n of getLinkedNodesFromOutput(graph, parentNode, 0)) queue.push(n);

  const children = [];
  while (queue.length) {
    const n = queue.shift();
    if (!n || visited.has(n.id)) continue;
    visited.add(n.id);

    if (n.comfyClass === CT_CHILD) {
      children.push(n);
      // allow chaining: Child output(0) -> Child input
      for (const next of getLinkedNodesFromOutput(graph, n, 0)) queue.push(next);
    }
  }
  return children;
}

// Apply bypass/enable to: parent group(s) + child groups (via connected child markers)
function applyCascadeBypassFromParent(graph, parentNode, bypass) {
  const groupsToToggle = new Set();

  // groups containing parent
  for (const g of findGroupsContainingNode(graph, parentNode)) {
    groupsToToggle.add(g);
  }

  // groups containing connected child markers
  const children = collectChildNodes(graph, parentNode);
  for (const child of children) {
    for (const g of findGroupsContainingNode(graph, child)) {
      groupsToToggle.add(g);
    }
  }

  for (const g of groupsToToggle) setGroupBypass(g, bypass);

  app.graph.setDirtyCanvas(true, true);
}

// If group contains Parent marker(s), toggle by cascading for each parent.
// Otherwise, toggle group only.
function toggleGroupWithCascadeIfNeeded(graph, group, bypass) {
  const parents = getParentNodesInGroup(graph, group);
  if (parents.length) {
    for (const p of parents) applyCascadeBypassFromParent(graph, p, bypass);
  } else {
    setGroupBypass(group, bypass);
    app.graph.setDirtyCanvas(true, true);
  }
}

// ------------------------- ordering (drag modal) -------------------------
function parseOrderString(orderStr) {
  if (!orderStr || typeof orderStr !== "string") return [];
  return orderStr.split(",").map((s) => s.trim()).filter((s) => s.length > 0);
}

function uniqPreserve(arr) {
  const seen = new Set();
  const out = [];
  for (const x of arr) {
    if (seen.has(x)) continue;
    seen.add(x);
    out.push(x);
  }
  return out;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function openDragOrderEditor(node, labels) {
  node._hybsCloseEditor?.();

  // labels: array of display labels (unique-enough)
  const currentLabels = labels.slice();
  const desired = uniqPreserve(parseOrderString(node.properties.order_titles || ""));
  const labelSet = new Set(currentLabels);
  const inDesired = desired.filter((t) => labelSet.has(t));
  const missing = currentLabels.filter((t) => !inDesired.includes(t));
  const initial = [...inDesired, ...missing];

  const overlay = document.createElement("div");
  overlay.className = "hybs-overlay";
  overlay.innerHTML = `
    <div class="hybs-modal" role="dialog" aria-modal="true">
      <div class="hybs-header">
        <div class="hybs-title">Group Order Editor</div>
        <button class="hybs-x" title="Close">×</button>
      </div>
      <div class="hybs-body">
        <div class="hybs-hint">Drag and drop to reorder. Click Save to apply.</div>
        <div class="hybs-list" tabindex="0"></div>
        <div class="hybs-actions">
          <button class="hybs-btn" data-action="auto">Auto</button>
          <button class="hybs-btn" data-action="reset">Reset</button>
          <div class="hybs-spacer"></div>
          <button class="hybs-btn hybs-btn-secondary" data-action="cancel">Cancel</button>
          <button class="hybs-btn hybs-btn-primary" data-action="save">Save</button>
        </div>
      </div>
    </div>
  `;

  const style = document.createElement("style");
  style.textContent = `
    .hybs-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:999999;display:flex;align-items:center;justify-content:center;padding:18px;}
    .hybs-modal{width:min(720px,96vw);max-height:min(80vh,820px);background:#1f1f1f;border:1px solid rgba(255,255,255,0.15);border-radius:10px;box-shadow:0 12px 40px rgba(0,0,0,0.6);display:flex;flex-direction:column;overflow:hidden;color:#e8e8e8;font:13px/1.4 sans-serif;}
    .hybs-header{padding:12px 14px;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(255,255,255,0.10);background:#242424;}
    .hybs-title{font-size:14px;font-weight:700;}
    .hybs-x{margin-left:auto;background:transparent;border:none;color:#e8e8e8;font-size:18px;cursor:pointer;line-height:1;padding:0 6px;opacity:0.85;}
    .hybs-x:hover{opacity:1;}
    .hybs-body{padding:14px;display:flex;flex-direction:column;gap:10px;overflow:hidden;}
    .hybs-hint{opacity:0.9;}
    .hybs-list{overflow:auto;border:1px solid rgba(255,255,255,0.10);border-radius:8px;background:#181818;padding:8px;min-height:140px;max-height:46vh;}
    .hybs-item{display:flex;align-items:center;gap:10px;padding:8px 10px;margin:6px 0;border-radius:8px;border:1px solid rgba(255,255,255,0.08);background:#202020;cursor:grab;user-select:none;}
    .hybs-item.dragging{opacity:0.55;}
    .hybs-handle{width:14px;opacity:0.75;font-family:monospace;}
    .hybs-drop-marker{height:0;border-top:2px solid rgba(255,255,255,0.55);margin:6px 0;}
    .hybs-actions{display:flex;align-items:center;gap:10px;padding-top:6px;}
    .hybs-spacer{flex:1;}
    .hybs-btn{border:1px solid rgba(255,255,255,0.14);background:#2a2a2a;color:#e8e8e8;border-radius:8px;padding:8px 12px;cursor:pointer;}
    .hybs-btn:hover{background:#313131;}
    .hybs-btn-secondary{background:#252525;}
    .hybs-btn-primary{background:#3a3a3a;border-color:rgba(255,255,255,0.22);font-weight:700;}
    .hybs-btn-primary:hover{background:#424242;}
  `;
  document.head.appendChild(style);

  const listEl = overlay.querySelector(".hybs-list");
  const closeBtn = overlay.querySelector(".hybs-x");

  function render(items) {
    listEl.innerHTML = "";
    for (const label of items) {
      const div = document.createElement("div");
      div.className = "hybs-item";
      div.draggable = true;
      div.dataset.label = label;
      div.innerHTML = `<div class="hybs-handle">⋮⋮</div><div>${escapeHtml(label)}</div>`;
      listEl.appendChild(div);
    }
  }

  // --- Drag logic (fixed: bottom->top works) ---
  let dragEl = null;
  const dropMarker = document.createElement("div");
  dropMarker.className = "hybs-drop-marker";

  function cleanupMarker() {
    if (dropMarker.parentElement) dropMarker.parentElement.removeChild(dropMarker);
  }

  listEl.addEventListener("dragenter", (e) => e.preventDefault());

  listEl.addEventListener("dragstart", (e) => {
    const item = e.target.closest(".hybs-item");
    if (!item) return;
    dragEl = item;
    item.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", item.dataset.label);
  });

  listEl.addEventListener("dragend", () => {
    if (dragEl) dragEl.classList.remove("dragging");
    dragEl = null;
    cleanupMarker();
  });

  listEl.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (!dragEl) return;

    const afterEl = (() => {
      const items = [...listEl.querySelectorAll(".hybs-item:not(.dragging)")];
      const y = e.clientY;
      let closest = { offset: Number.NEGATIVE_INFINITY, el: null };
      for (const child of items) {
        const box = child.getBoundingClientRect();
        const offset = y - (box.top + box.height / 2);
        if (offset < 0 && offset > closest.offset) {
          closest = { offset, el: child };
        }
      }
      return closest.el;
    })();

    cleanupMarker();
    if (afterEl == null) listEl.appendChild(dropMarker);
    else listEl.insertBefore(dropMarker, afterEl);
  });

  listEl.addEventListener("drop", (e) => {
    e.preventDefault();
    if (!dragEl) return;

    const markerParent = dropMarker.parentElement;
    if (!markerParent) return;

    markerParent.insertBefore(dragEl, dropMarker);
    cleanupMarker();
  });

  function getCurrentOrder() {
    return Array.from(listEl.querySelectorAll(".hybs-item")).map((x) => x.dataset.label);
  }

  function close() {
    overlay.remove();
    style.remove();
    if (node._hybsCloseEditor === close) {
      node._hybsCloseEditor = null;
    }
  }

  closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });

  overlay.querySelector("[data-action='cancel']").addEventListener("click", close);

  overlay.querySelector("[data-action='reset']").addEventListener("click", () => {
    render(currentLabels);
  });

  overlay.querySelector("[data-action='auto']").addEventListener("click", () => {
    node.properties.order_mode = "auto";
    node.properties.order_titles = "";
    node._hybsRebuild?.(true);
    close();
  });

  overlay.querySelector("[data-action='save']").addEventListener("click", () => {
    node.properties.order_mode = "custom";
    node.properties.order_titles = getCurrentOrder().join(", ");
    node._hybsRebuild?.(true);
    close();
  });

  render(initial);
  node._hybsCloseEditor = close;
  document.body.appendChild(overlay);
  return close;
}

// ------------------------- ComfyUI extension hook -------------------------
app.registerExtension({
  name: "HYBS.GroupBypasser.PanelOnly",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    const classType = nodeData?.name;

    // Parent / Child: no UI added (Panel only toggles)
    if (classType === CT_PARENT || classType === CT_CHILD) return;

    // Panel UI
    if (classType === CT_PANEL) {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        onNodeCreated?.apply(this, arguments);

        this.properties = this.properties || {};
        if (this.properties.order_mode === undefined) this.properties.order_mode = "auto";
        if (this.properties.order_titles === undefined) this.properties.order_titles = "";
        this._hybsNeedsSync = true;
        this._hybsLastSyncAt = 0;

        // UI widgets
        this.addWidget("combo", "order mode", this.properties.order_mode, (v) => {
          this.properties.order_mode = v;
          this._hybsNeedsSync = true;
          this._hybsRebuild?.(true);
        }, { values: ["auto", "custom"] });

        this.addWidget("string", "order titles", this.properties.order_titles, (v) => {
          this.properties.order_titles = v;
          this._hybsNeedsSync = true;
          this._hybsRebuild?.(true);
        }, { multiline: true });

        this.addWidget("button", "edit order", "edit", () => {
          // Pass labels (Main + subgraphs)
          const allGraphs = getAllGraphs(app.graph);
          const labels = [];
          for (const gr of allGraphs) {
            const glabel = getGraphLabel(gr);
            for (const gp of getGroups(gr)) {
              labels.push(`[${glabel}] ${getGroupTitle(gp)}`);
            }
          }
          this._hybsNeedsSync = true;
          openDragOrderEditor(this, labels);
        });

        this.addWidget("button", "refresh", "refresh", () => {
          this._hybsNeedsSync = true;
          this._hybsRebuild?.(true);
        });

        // static widget count (everything after this is dynamic toggles)
        this._hybsStaticCount = this.widgets?.length || 0;

        this._hybsRebuild = (force) => {
          const allGraphs = getAllGraphs(app.graph);

          // Build entries: [{ graph, group, label, index }]
          const entries = [];
          let idx = 0;
          for (const gr of allGraphs) {
            const glabel = getGraphLabel(gr);
            const groups = getGroups(gr);
            for (const gp of groups) {
              const label = `[${glabel}] ${getGroupTitle(gp)}`;
              entries.push({ graph: gr, group: gp, label, idx: idx++ });
            }
          }

          const labels = entries.map((e) => e.label);
          const sig = `${labels.length}:${labels.join("|")}`;
          if (!force && sig === this._hybsSig) return;
          this._hybsSig = sig;

          // remove dynamic toggles safely
          if (this.widgets && this.widgets.length > this._hybsStaticCount) {
            this.widgets.splice(this._hybsStaticCount);
          }

          // order entries
          let ordered = entries.map((e) => e);
          if (this.properties.order_mode === "custom") {
            const desired = uniqPreserve(parseOrderString(this.properties.order_titles));
            if (desired.length) {
              const desiredIndex = new Map();
              desired.forEach((t, i) => { if (!desiredIndex.has(t)) desiredIndex.set(t, i); });

              ordered = entries
                .map((e) => ({ ...e, key: desiredIndex.has(e.label) ? desiredIndex.get(e.label) : Number.POSITIVE_INFINITY }))
                .sort((a, b) => {
                  if (a.key !== b.key) return a.key - b.key;
                  return a.idx - b.idx;
                });
            }
          }

          // build toggles (graph-aware)
          for (const e of ordered) {
            const hasParent = groupHasParentNode(e.graph, e.group);
            const label = hasParent ? `${e.label} (cascade)` : e.label;

            const w = this.addWidget("toggle", label, isGroupBypassed(e.group), (v) => {
              toggleGroupWithCascadeIfNeeded(e.graph, e.group, !!v);
              this._hybsNeedsSync = true;
              // Force immediate UI rebind so cascade-target toggles reflect new state.
              this._hybsRebuild?.(true);
              app.graph?.setDirtyCanvas?.(true, true);
            });

            w._hybsGraph = e.graph;
            w._hybsGroup = e.group;
          }

          this.setSize([this.size[0], Math.max(240, 120 + ordered.length * 28)]);
          this._hybsNeedsSync = true;
          app.graph.setDirtyCanvas(true, true);
        };

        this._hybsSyncToggleState = () => {
          const start = this._hybsStaticCount ?? 0;
          for (let i = start; i < (this.widgets?.length || 0); i++) {
            const w = this.widgets[i];
            if (!w || w.type !== "toggle") continue;
            const g = w._hybsGroup;
            if (!g) continue;
            w.value = isGroupBypassed(g);
          }
        };

        this._hybsRebuild(true);
        // Workflow load timing can delay group availability. Rebuild again shortly after creation.
        const scheduleBootstrapRebuild = (delayMs) => {
          setTimeout(() => {
            try {
              this._hybsNeedsSync = true;
              this._hybsRebuild?.(true);
              app.graph?.setDirtyCanvas?.(true, true);
            } catch (_) {}
          }, delayMs);
        };
        scheduleBootstrapRebuild(0);
        scheduleBootstrapRebuild(200);
      };

      const onConfigure = nodeType.prototype.onConfigure;
      nodeType.prototype.onConfigure = function () {
        onConfigure?.apply(this, arguments);
        try {
          this._hybsNeedsSync = true;
          this._hybsRebuild?.(true);
          app.graph?.setDirtyCanvas?.(true, true);
        } catch (_) {}
      };

      const onRemoved = nodeType.prototype.onRemoved;
      nodeType.prototype.onRemoved = function () {
        try { this._hybsCloseEditor?.(); } catch (_) {}
        onRemoved?.apply(this, arguments);
      };

      // keep toggle states synced
      const onDrawForeground = nodeType.prototype.onDrawForeground;
      nodeType.prototype.onDrawForeground = function () {
        onDrawForeground?.apply(this, arguments);

        const now = Date.now();
        const last = this._hybsLastSyncAt || 0;
        if (!this._hybsNeedsSync && now - last < PANEL_SYNC_INTERVAL_MS) {
          return;
        }
        this._hybsLastSyncAt = now;

        try { this._hybsSyncToggleState?.(); } catch (_) {}
        try { this._hybsRebuild?.(false); } catch (_) {}
        this._hybsNeedsSync = false;
      };
    }
  }
});

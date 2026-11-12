import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY } from "d3-force";
import { api } from "../api";

const W = 900;
const H = 600;

function score(n) {
  return n.fan_in + 0.5 * n.fan_out;
}

function computeLayout(nodes, edges) {
  const max = Math.max(...nodes.map(score), 1);
  const sim = nodes.map((n, i) => {
    const a = (i / nodes.length) * Math.PI * 2;
    return {
      id: n.id,
      r: 7 + 17 * Math.sqrt(score(n) / max),
      x: W / 2 + Math.cos(a) * 160,
      y: H / 2 + Math.sin(a) * 130,
    };
  });
  const links = edges.map((e) => ({ source: e.from, target: e.to }));
  const f = forceSimulation(sim)
    .force("link", forceLink(links).id((d) => d.id).distance(95).strength(0.4))
    .force("charge", forceManyBody().strength(-360).distanceMax(320))
    .force("gx", forceX(W / 2).strength(0.12))
    .force("gy", forceY(H / 2).strength(0.16))
    .force("center", forceCenter(W / 2, H / 2))
    .force("collide", forceCollide((d) => d.r + 34))
    .stop();
  for (let i = 0; i < 320; i++) f.tick();
  return Object.fromEntries(sim.map((s) => [s.id, { x: s.x, y: s.y, r: s.r }]));
}

function fitView(pos) {
  const pts = Object.values(pos);
  if (!pts.length) return { x: 0, y: 0, k: 1 };
  const minX = Math.min(...pts.map((p) => p.x - p.r - 30));
  const maxX = Math.max(...pts.map((p) => p.x + p.r + 30));
  const minY = Math.min(...pts.map((p) => p.y - p.r - 12));
  const maxY = Math.max(...pts.map((p) => p.y + p.r + 28));
  const AH = H - 44; // keep the bottom strip free for the hint text
  const k = Math.min((W * 0.96) / (maxX - minX), (AH * 0.92) / (maxY - minY), 1.8);
  return { k, x: W / 2 - ((minX + maxX) / 2) * k, y: AH / 2 - ((minY + maxY) / 2) * k };
}

export default function CodeMap({ repoId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [pos, setPos] = useState({});
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [selected, setSelected] = useState(null);
  const [group, setGroup] = useState(null); // ids highlighted from the health panel
  const [impact, setImpact] = useState(null);
  const [explain, setExplain] = useState({ loading: false, text: null });
  const svgRef = useRef(null);
  const drag = useRef(null);

  useEffect(() => {
    setData(null);
    setError(null);
    setSelected(null);
    api
      .map(repoId)
      .then((d) => {
        setData(d);
        const layout = d.nodes.length ? computeLayout(d.nodes, d.edges) : {};
        setPos(layout);
        setView(fitView(layout));
      })
      .catch((e) => setError(e.message));
  }, [repoId]);

  useEffect(() => {
    setImpact(null);
    setExplain({ loading: false, text: null });
    if (selected == null) return;
    let live = true;
    api.impact(repoId, selected).then((r) => live && setImpact(r)).catch(() => {});
    return () => {
      live = false;
    };
  }, [selected, repoId]);

  // wheel zoom needs a non-passive listener so the page does not scroll
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    function onWheel(e) {
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      const px = ((e.clientX - rect.left) * W) / rect.width;
      const py = ((e.clientY - rect.top) * H) / rect.height;
      setView((v) => {
        const k = Math.min(3, Math.max(0.35, v.k * (1 - e.deltaY * 0.0012)));
        return { k, x: px - (px - v.x) * (k / v.k), y: py - (py - v.y) * (k / v.k) };
      });
    }
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  });

  const byId = useMemo(() => Object.fromEntries((data?.nodes || []).map((n) => [n.id, n])), [data]);

  // what role does each node play for the current selection?
  const roles = useMemo(() => {
    const r = {};
    if (selected != null && impact && impact.file.id === selected) {
      impact.uses.forEach((f) => (r[f.id] = "uses"));
      impact.indirect.forEach((f) => (r[f.id] = "indirect"));
      impact.direct.forEach((f) => (r[f.id] = "direct"));
      r[selected] = "selected";
    } else if (selected != null) {
      r[selected] = "selected";
    } else if (group) {
      group.forEach((id) => (r[id] = "group"));
    }
    return r;
  }, [selected, impact, group]);
  const focusing = Object.keys(roles).length > 0;

  function scale() {
    const rect = svgRef.current.getBoundingClientRect();
    return W / rect.width;
  }

  function onNodeDown(e, id) {
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { type: "node", id, sx: e.clientX, sy: e.clientY, moved: 0 };
  }
  function onBgDown(e) {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { type: "pan", sx: e.clientX, sy: e.clientY, moved: 0 };
  }
  function onMove(e) {
    const d = drag.current;
    if (!d) return;
    const s = scale();
    const dx = (e.clientX - d.sx) * s;
    const dy = (e.clientY - d.sy) * s;
    d.moved += Math.abs(dx) + Math.abs(dy);
    d.sx = e.clientX;
    d.sy = e.clientY;
    if (d.type === "pan") setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
    else setPos((p) => ({ ...p, [d.id]: { ...p[d.id], x: p[d.id].x + dx / view.k, y: p[d.id].y + dy / view.k } }));
  }
  function onUp() {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    if (d.moved < 4) {
      if (d.type === "node") {
        setGroup(null);
        setSelected((cur) => (cur === d.id ? null : d.id));
      } else {
        setSelected(null);
        setGroup(null);
      }
    }
  }

  function pick(id) {
    if (byId[id]) {
      setGroup(null);
      setSelected(id);
    }
  }

  async function runExplain() {
    const path = byId[selected]?.path;
    setExplain({ loading: true, text: null });
    try {
      const res = await api.explain(repoId, `Explain what ${path} does in simple language and how other files use it.`);
      setExplain({ loading: false, text: res.answer });
    } catch (e) {
      setExplain({ loading: false, text: "Error: " + e.message });
    }
  }

  if (error) return <p role="alert" className="text-sm text-maroon">{error}</p>;
  if (!data) return <p className="animate-pulse text-sm text-ink/55">Drawing the map…</p>;
  if (data.nodes.length === 0)
    return (
      <p className="rounded-xl border border-line bg-white p-6 text-sm text-ink/70">
        No import links were found between Python files, so there is nothing to draw yet.
      </p>
    );

  const sel = selected != null ? byId[selected] : null;

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink/70">
        <span><b className="font-display text-lg text-ink">{data.stats.files}</b> source files</span>
        <span><b className="font-display text-lg text-ink">{data.stats.links}</b> import links</span>
        <span>
          <b className={`font-display text-lg ${data.stats.cycle_groups ? "text-maroon" : "text-ink"}`}>
            {data.stats.cycle_groups}
          </b>{" "}
          circular import {data.stats.cycle_groups === 1 ? "group" : "groups"}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_21rem]">
        <div className="relative h-fit overflow-hidden rounded-xl border border-line bg-white">
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className="block h-auto w-full touch-none select-none"
            role="img"
            aria-label="Dependency map of the repository"
            onPointerMove={onMove}
            onPointerUp={onUp}
          >
            <defs>
              {[["a-grey", "#c4b5fd"], ["a-maroon", "#e11d48"], ["a-navy", "#6366f1"]].map(([id, c]) => (
                <marker key={id} id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M0 0L10 5L0 10z" fill={c} />
                </marker>
              ))}
            </defs>
            <rect width={W} height={H} fill="transparent" onPointerDown={onBgDown} className="cursor-grab" />
            <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
              {data.edges.map((e, i) => {
                const a = pos[e.from];
                const b = pos[e.to];
                if (!a || !b) return null;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const len = Math.hypot(dx, dy) || 1;
                const ux = dx / len;
                const uy = dy / len;
                const x1 = a.x + ux * (a.r + 2);
                const y1 = a.y + uy * (a.r + 2);
                const x2 = b.x - ux * (b.r + 5);
                const y2 = b.y - uy * (b.r + 5);
                const off = Math.min(26, len * 0.12);
                const cx = (x1 + x2) / 2 - uy * off;
                const cy = (y1 + y2) / 2 + ux * off;
                const ra = roles[e.from];
                const rb = roles[e.to];
                let color = "grey";
                let op = focusing ? 0.07 : 0.45;
                if (focusing && ra && rb) {
                  const imp = (r) => r === "selected" || r === "direct" || r === "indirect" || r === "group";
                  color = imp(ra) && imp(rb) ? "maroon" : "navy";
                  op = 0.9;
                }
                return (
                  <path
                    key={i}
                    d={`M${x1} ${y1}Q${cx} ${cy} ${x2} ${y2}`}
                    fill="none"
                    stroke={color === "maroon" ? "#e11d48" : color === "navy" ? "#6366f1" : "#c4b5fd"}
                    strokeWidth={color === "grey" ? 1.2 : 1.8}
                    strokeOpacity={op}
                    markerEnd={`url(#a-${color})`}
                  />
                );
              })}

              {data.nodes.map((n) => {
                const p = pos[n.id];
                if (!p) return null;
                const role = roles[n.id];
                let fill = ["#6366f1", "#0ea5e9", "#ec4899", "#f97316", "#14b8a6", "#a855f7"][n.id % 6];
                let fo = 1;
                let stroke = n.god ? "#e11d48" : "#ffffff";
                let sw = n.god ? 3 : 2;
                if (role === "selected") { fill = "#1b1740"; stroke = "#e11d48"; sw = 3.5; }
                else if (role === "direct") fill = "#e11d48";
                else if (role === "indirect") { fill = "#e11d48"; fo = 0.45; }
                else if (role === "uses") fill = "#38bdf8";
                else if (role === "group") { fill = "#e11d48"; fo = 0.85; }
                const dim = focusing && !role;
                return (
                  <g
                    key={n.id}
                    transform={`translate(${p.x} ${p.y})`}
                    opacity={dim ? 0.22 : 1}
                    className="cursor-pointer"
                    onPointerDown={(e) => onNodeDown(e, n.id)}
                  >
                    <title>{n.path}</title>
                    <circle r={p.r} fill={fill} fillOpacity={fo} stroke={stroke} strokeWidth={sw} />
                    <text
                      y={p.r + 14}
                      textAnchor="middle"
                      className="font-mono"
                      fontSize="11"
                      fill="#1b1740"
                      stroke="#ffffff"
                      strokeWidth="3.5"
                      paintOrder="stroke"
                    >
                      {n.label}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          <div className="pointer-events-none absolute bottom-3 left-4 right-4 flex flex-wrap items-center justify-between gap-2 text-xs text-ink/60">
            <span>Scroll to zoom, drag to move. Click a file to see what depends on it.</span>
            <button
              onClick={() => setView(fitView(pos))}
              className="pointer-events-auto rounded border border-line bg-white px-2 py-1 hover:border-navy hover:text-navy"
            >
              Reset view
            </button>
          </div>
        </div>

        <aside className="h-fit rounded-xl border border-line bg-white p-5">
          {sel ? (
            <SelectedPanel
              sel={sel}
              impact={impact}
              explain={explain}
              onExplain={runExplain}
              onPick={pick}
              onClose={() => setSelected(null)}
              inMap={(id) => !!byId[id]}
            />
          ) : (
            <HealthPanel health={data.health} byId={byId} onPick={pick} onGroup={(ids) => setGroup(ids)} activeGroup={group} />
          )}
        </aside>
      </div>
    </div>
  );
}

function FileLink({ f, onPick, inMap }) {
  const can = inMap(f.id);
  return (
    <li>
      <button
        disabled={!can}
        onClick={() => onPick(f.id)}
        title={can ? "Show on the map" : "Not drawn on the map"}
        className={`break-all text-left font-mono text-xs ${can ? "text-navy hover:underline" : "text-ink/50"}`}
      >
        {f.path}
      </button>
    </li>
  );
}

function SelectedPanel({ sel, impact, explain, onExplain, onPick, onClose, inMap }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <h3 className="break-all font-mono text-sm font-medium text-ink">{sel.path}</h3>
        <button onClick={onClose} aria-label="Clear selection" className="text-ink/45 hover:text-ink">✕</button>
      </div>
      <dl className="mt-3 grid grid-cols-4 gap-2 text-center">
        {[["Imported by", sel.fan_in], ["Imports", sel.fan_out], ["Lines", sel.loc], ["Functions and classes", sel.symbols]].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-paper px-1 py-2">
            <dd className="font-display text-lg font-bold">{v}</dd>
            <dt className="text-[10px] leading-tight text-ink/55">{k}</dt>
          </div>
        ))}
      </dl>

      {!impact ? (
        <p className="mt-5 animate-pulse text-sm text-ink/50">Working out what depends on this file…</p>
      ) : (
        <div className="mt-5">
          <p className="font-display text-base font-semibold">
            If you change this file, <span className="text-maroon">{impact.total}</span>{" "}
            {impact.total === 1 ? "file" : "files"} may be affected
          </p>
          <p className="mt-1 text-xs text-ink/60">
            {impact.direct.length} import it directly, {impact.indirect.length} depend on it through other files.
          </p>

          {impact.direct.length > 0 && (
            <>
              <h4 className="mt-4 text-sm font-semibold text-maroon">Directly affected</h4>
              <ul className="mt-1.5 max-h-32 space-y-1 overflow-y-auto">
                {impact.direct.map((f) => <FileLink key={f.id} f={f} onPick={onPick} inMap={inMap} />)}
              </ul>
            </>
          )}
          {impact.indirect.length > 0 && (
            <>
              <h4 className="mt-4 text-sm font-semibold text-maroon/70">Affected through others</h4>
              <ul className="mt-1.5 max-h-32 space-y-1 overflow-y-auto">
                {impact.indirect.map((f) => <FileLink key={f.id} f={f} onPick={onPick} inMap={inMap} />)}
              </ul>
            </>
          )}
          {impact.uses.length > 0 && (
            <>
              <h4 className="mt-4 text-sm font-semibold text-navy">It relies on</h4>
              <ul className="mt-1.5 max-h-28 space-y-1 overflow-y-auto">
                {impact.uses.map((f) => <FileLink key={f.id} f={f} onPick={onPick} inMap={inMap} />)}
              </ul>
            </>
          )}
        </div>
      )}

      <button
        onClick={onExplain}
        disabled={explain.loading}
        className="mt-5 w-full rounded-lg bg-navy px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
      >
        {explain.loading ? "Reading the file…" : "Explain this file"}
      </button>
      {explain.text && (
        <div className="mt-4 border-l-2 border-navy pl-3 text-sm leading-relaxed text-ink/85 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_code]:rounded [&_code]:bg-mist [&_code]:px-1 [&_code]:font-mono [&_code]:text-[12px]">
          <ReactMarkdown>{explain.text}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

function HealthPanel({ health, byId, onPick, onGroup, activeGroup }) {
  const base = (p) => p.split("/").pop();
  return (
    <div>
      <h3 className="font-display text-lg font-semibold tracking-tight">Architecture health</h3>
      <p className="mt-1 text-xs text-ink/55">Found by analysing the import graph. Click an item to see it on the map.</p>

      <section className="mt-5">
        <h4 className="text-sm font-semibold">Circular imports</h4>
        {health.cycles.length === 0 ? (
          <p className="mt-1 text-xs text-ink/60">None found. No file depends on itself through a loop.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {health.cycles.slice(0, 5).map((c, i) => {
              const ids = c.files.map((f) => f.id);
              const active = activeGroup && activeGroup.length === ids.length && ids.every((x) => activeGroup.includes(x));
              return (
                <li key={i}>
                  <button
                    onClick={() => onGroup(active ? null : ids)}
                    className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${active ? "border-maroon bg-maroon/5" : "border-line hover:border-maroon"}`}
                  >
                    <span className="font-semibold text-maroon">{c.size} files</span> import each other in a loop
                    <span className="mt-1 block font-mono text-[11px] text-ink/55">
                      {c.files.slice(0, 3).map((f) => base(f.path)).join(", ")}
                      {c.files.length > 3 ? ` and ${c.files.length - 3} more` : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="mt-5">
        <h4 className="text-sm font-semibold">Heavily coupled files</h4>
        {health.coupled.length === 0 ? (
          <p className="mt-1 text-xs text-ink/60">None. No file is both heavily used and heavily dependent.</p>
        ) : (
          <>
            <p className="mt-1 text-xs text-ink/55">Both import and are imported by many files, so changes here ripple widely.</p>
            <ul className="mt-2 space-y-1.5">
              {health.coupled.map((f) => (
                <li key={f.id}>
                  <button onClick={() => onPick(f.id)} className="break-all text-left font-mono text-xs text-navy hover:underline">
                    {f.path}
                  </button>
                  <span className="ml-2 text-[11px] text-ink/50">in {f.fan_in}, out {f.fan_out}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="mt-5">
        <h4 className="text-sm font-semibold">Files with no import links</h4>
        {health.isolated_total === 0 ? (
          <p className="mt-1 text-xs text-ink/60">None.</p>
        ) : (
          <>
            <p className="mt-1 text-xs text-ink/55">
              {health.isolated_total} {health.isolated_total === 1 ? "file neither imports" : "files neither import"} nor {health.isolated_total === 1 ? "is" : "are"} imported. They are entry points, scripts, or possibly unused.
            </p>
            <ul className="mt-2 space-y-1">
              {health.isolated.slice(0, 6).map((f) => (
                <li key={f.id} className="break-all font-mono text-xs text-ink/70">{f.path}</li>
              ))}
              {health.isolated_total > 6 && <li className="text-xs text-ink/45">and {health.isolated_total - 6} more</li>}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}

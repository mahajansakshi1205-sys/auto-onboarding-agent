import { useEffect, useState } from "react";
import { api, BASE } from "../api";

const TILE = [
  "from-indigo-500 to-violet-500 shadow-indigo-300/60",
  "from-sky-500 to-teal-400 shadow-sky-300/60",
  "from-pink-500 to-rose-500 shadow-pink-300/60",
  "from-orange-500 to-amber-400 shadow-orange-300/60",
];
const BAR = [
  "from-indigo-500 to-violet-400", "from-sky-500 to-cyan-400", "from-pink-500 to-rose-400",
  "from-orange-500 to-amber-400", "from-teal-500 to-emerald-400", "from-fuchsia-500 to-purple-400",
  "from-blue-500 to-indigo-400", "from-rose-500 to-orange-400",
];

export default function Overview({ repoId }) {
  const [map, setMap] = useState(null);

  useEffect(() => {
    setMap(null);
    api.map(repoId).then(setMap).catch(() => setMap(false));
  }, [repoId]);

  const ranked = map ? [...map.nodes].sort((a, b) => b.fan_in + b.fan_out - (a.fan_in + a.fan_out)).slice(0, 8) : [];
  const maxDeg = Math.max(...ranked.map((n) => n.fan_in + n.fan_out), 1);
  const tiles = map
    ? [
        ["Source files", map.stats.files, "Python files analysed"],
        ["Import links", map.stats.links, "who imports whom"],
        ["Circular groups", map.stats.cycle_groups, map.stats.cycle_groups ? "files that import in a loop" : "no loops found"],
        ["Most connected", ranked[0]?.label ?? "-", ranked[0] ? `${ranked[0].fan_in + ranked[0].fan_out} links` : ""],
      ]
    : [];

  return (
    <div className="space-y-6">
      {tiles.length > 0 && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {tiles.map(([k, v, note], i) => (
            <div key={k} className={`rounded-2xl bg-gradient-to-br ${TILE[i]} p-5 text-white shadow-xl`}>
              <div className="text-xs font-medium text-white/80">{k}</div>
              <div className={`mt-1 font-display font-extrabold leading-tight ${String(v).length > 8 ? "text-xl break-all" : "text-4xl"}`}>{v}</div>
              <div className="mt-1 text-xs text-white/75">{note}</div>
            </div>
          ))}
        </div>
      )}

      {ranked.length > 0 && (
        <div className="rounded-2xl border border-line bg-white p-6 shadow-[0_18px_40px_-28px_rgba(91,33,182,0.5)]">
          <h3 className="font-display text-xl font-bold tracking-tight">Most connected files</h3>
          <p className="mt-1 text-sm text-ink/60">Files with the most import links in and out. Change these with care.</p>
          <ul className="mt-5 space-y-3">
            {ranked.map((n, i) => (
              <li key={n.id}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="break-all font-mono text-[13px] text-ink">{n.path}</span>
                  <span className="shrink-0 text-xs text-ink/55">in {n.fan_in}, out {n.fan_out}</span>
                </div>
                <div className="mt-1.5 h-2.5 rounded-full bg-mist">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${BAR[i % BAR.length]}`}
                    style={{ width: `${((n.fan_in + n.fan_out) / maxDeg) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl border border-line bg-white p-6 shadow-[0_18px_40px_-28px_rgba(91,33,182,0.5)]">
        <h3 className="font-display text-xl font-bold tracking-tight">Importance ranking</h3>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink/60">
          Files score higher when many files import them, when they import a lot themselves, and when they are large.
          Tests and docs are left out.
        </p>
        <img src={`${BASE}/repos/${repoId}/analytics/chart?cache=${repoId}`} alt="Bar chart of the most important files" className="mt-4 w-full" />
      </div>
    </div>
  );
}

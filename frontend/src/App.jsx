import { useEffect, useState } from "react";
import { api } from "./api";
import Route from "./components/Route";
import Dashboard from "./components/Dashboard";

const STEPS = [
  { key: "ingest", label: "Clone", note: "Fetch the repository", from: "#0ea5e9", to: "#6366f1" },
  { key: "parse", label: "Parse", note: "Find functions and classes", from: "#8b5cf6", to: "#d946ef" },
  { key: "graph", label: "Map", note: "Link files that import each other", from: "#ec4899", to: "#f43f5e" },
  { key: "index", label: "Index", note: "Make the code searchable", from: "#f97316", to: "#f59e0b" },
];

const FEATURES = [
  ["Dependency map", "bg-sky-400/20 text-sky-100 ring-sky-300/40"],
  ["Impact analysis", "bg-pink-400/20 text-pink-100 ring-pink-300/40"],
  ["Reading order", "bg-emerald-400/20 text-emerald-100 ring-emerald-300/40"],
  ["Answers with sources", "bg-amber-400/20 text-amber-100 ring-amber-300/40"],
];

function MiniMap() {
  const nodes = [
    [70, 60, 22, "#38bdf8"], [190, 40, 14, "#f472b6"], [260, 120, 26, "#a78bfa"], [120, 150, 18, "#fb923c"],
    [40, 190, 12, "#34d399"], [200, 230, 20, "#f472b6"], [310, 220, 12, "#38bdf8"], [150, 290, 14, "#fbbf24"],
  ];
  const links = [[0, 1], [0, 3], [1, 2], [2, 3], [3, 4], [2, 5], [3, 5], [5, 6], [5, 7], [4, 7], [2, 6]];
  return (
    <svg viewBox="0 0 360 330" className="w-full max-w-sm drop-shadow-2xl" aria-hidden="true">
      {links.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke="white" strokeOpacity="0.35" strokeWidth="1.5" />
      ))}
      {nodes.map(([x, y, r, c], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={r + 9} fill={c} fillOpacity="0.18" />
          <circle cx={x} cy={y} r={r} fill={c} />
        </g>
      ))}
    </svg>
  );
}

export default function App() {
  const [backendUp, setBackendUp] = useState(null);
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState({});
  const [repoId, setRepoId] = useState(null);
  const [repoName, setRepoName] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.health().then(() => setBackendUp(true)).catch(() => setBackendUp(false));
  }, []);

  async function run(key, fn) {
    setStatus((s) => ({ ...s, [key]: "running" }));
    const result = await fn();
    setStatus((s) => ({ ...s, [key]: "done" }));
    return result;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setStatus({});
    setRepoId(null);
    try {
      const repo = await run("ingest", () => api.ingest(url));
      const id = repo.id ?? repo.repo_id;
      await run("parse", () => api.parse(id));
      await run("graph", () => api.buildGraph(id));
      await run("index", () => api.index(id));
      setRepoName(url.replace(/^https?:\/\/github\.com\//, "").replace(/\/$/, ""));
      setRepoId(id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="relative overflow-hidden bg-gradient-to-br from-[#1a1150] via-[#3b1a8a] to-[#b0207a] text-white">
        <div className="dotgrid absolute inset-0" />
        <div className="pointer-events-none absolute -right-20 -top-28 h-96 w-96 rounded-full bg-pink-500/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-10 h-96 w-96 rounded-full bg-sky-400/30 blur-3xl" />
        <div className="pointer-events-none absolute right-1/3 top-1/2 h-72 w-72 rounded-full bg-orange-400/25 blur-3xl" />

        <div className="relative mx-auto max-w-5xl px-6">
          <nav className="flex items-center justify-between py-5 text-sm">
            <span className="font-display text-base font-semibold tracking-tight">Auto-Onboarding Agent</span>
            <span className="flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-white/80 ring-1 ring-white/20">
              <span className={`h-2 w-2 rounded-full ${backendUp ? "bg-emerald-400" : backendUp === false ? "bg-rose-400" : "bg-white/40"}`} />
              {backendUp === null && "Checking backend"}
              {backendUp === true && "Backend connected"}
              {backendUp === false && "Backend not running"}
            </span>
          </nav>

          <div className="grid items-center gap-8 pb-32 pt-10 lg:grid-cols-[1.25fr_1fr] lg:pt-14">
            <div>
              <h1 className="font-display text-4xl font-extrabold leading-[1.04] tracking-tight sm:text-6xl">
                Know a codebase before your first commit.
              </h1>
              <p className="mt-5 max-w-xl text-lg leading-relaxed text-white/75">
                Paste a public GitHub repository. You get the files that matter, the order to read them in,
                what breaks when you change a file, and answers that point to the exact lines.
              </p>

              <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-3 sm:flex-row">
                <input
                  type="url"
                  required
                  aria-label="GitHub repository URL"
                  placeholder="https://github.com/pallets/flask"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="flex-1 rounded-xl border border-white/25 bg-white/15 px-4 py-3.5 font-mono text-sm text-white placeholder:text-white/50 backdrop-blur focus:border-white/70 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-gradient-to-r from-orange-400 via-pink-500 to-fuchsia-500 px-6 py-3.5 font-semibold text-white shadow-lg shadow-pink-900/40 transition hover:brightness-110 disabled:opacity-60"
                >
                  {busy ? "Analyzing…" : "Analyze repository"}
                </button>
              </form>

              <div className="mt-6 flex flex-wrap gap-2">
                {FEATURES.map(([t, c]) => (
                  <span key={t} className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${c}`}>{t}</span>
                ))}
              </div>
            </div>

            <div className="hidden justify-center lg:flex">
              <MiniMap />
            </div>
          </div>
        </div>
      </header>

      <main className="relative mx-auto -mt-16 max-w-5xl px-6 pb-20">
        <Route steps={STEPS} status={status} />

        {error && (
          <p role="alert" className="mt-4 rounded-xl border border-rose-300 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </p>
        )}

        {repoId && <Dashboard repoId={repoId} repoName={repoName} />}
      </main>
    </div>
  );
}

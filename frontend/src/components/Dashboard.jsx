import { useState } from "react";
import Overview from "./Overview";
import Checklist from "./Checklist";
import Chat from "./Chat";
import CodeMap from "./CodeMap";

const TABS = [
  { name: "Key files", grad: "from-indigo-500 to-violet-500", glow: "shadow-indigo-400/50" },
  { name: "Code map", grad: "from-pink-500 to-rose-500", glow: "shadow-pink-400/50" },
  { name: "Reading order", grad: "from-teal-500 to-sky-500", glow: "shadow-teal-400/50" },
  { name: "Ask the code", grad: "from-orange-500 to-amber-500", glow: "shadow-orange-400/50" },
];

export default function Dashboard({ repoId, repoName }) {
  const [tab, setTab] = useState(TABS[0].name);

  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="bg-gradient-to-r from-indigo-600 via-fuchsia-500 to-orange-500 bg-clip-text font-display text-3xl font-extrabold tracking-tight text-transparent">
          {repoName}
        </h2>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Analysis complete</span>
      </div>

      <div role="tablist" className="mt-5 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.name}
            role="tab"
            aria-selected={tab === t.name}
            onClick={() => setTab(t.name)}
            className={`rounded-full px-5 py-2 text-sm font-semibold transition ${
              tab === t.name
                ? `bg-gradient-to-r ${t.grad} text-white shadow-lg ${t.glow}`
                : "border border-line bg-white text-ink/70 hover:border-indigo-300 hover:text-ink"
            }`}
          >
            {t.name}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "Key files" && <Overview repoId={repoId} />}
        {tab === "Code map" && <CodeMap repoId={repoId} />}
        {tab === "Reading order" && <Checklist repoId={repoId} />}
        {tab === "Ask the code" && <Chat repoId={repoId} />}
      </div>
    </section>
  );
}

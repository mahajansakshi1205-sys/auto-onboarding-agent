import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api";

const BAR = [
  "from-indigo-500 to-violet-400", "from-sky-500 to-cyan-400", "from-pink-500 to-rose-400",
  "from-orange-500 to-amber-400", "from-teal-500 to-emerald-400", "from-fuchsia-500 to-purple-400",
  "from-blue-500 to-indigo-400", "from-rose-500 to-orange-400",
];

export default function Checklist({ repoId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.checklist(repoId, 8).then(setData).catch((e) => setError(e.message));
  }, [repoId]);

  if (error) return <p role="alert" className="text-sm text-rose-600">{error}</p>;
  if (!data) return <p className="animate-pulse text-sm text-ink/55">Writing the reading order from the code…</p>;

  const max = Math.max(...data.files.map((f) => f.imported_by), 1);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <div className="rounded-2xl border border-line bg-white p-6 shadow-[0_18px_40px_-28px_rgba(13,148,136,0.55)]">
        <div className="-mx-6 -mt-6 mb-5 rounded-t-2xl bg-gradient-to-r from-teal-500 to-sky-500 px-6 py-4">
          <h3 className="font-display text-xl font-bold tracking-tight text-white">Read these in this order</h3>
          <p className="text-sm text-white/80">Start at the top. Each file builds on the one before it.</p>
        </div>
        <div className="steps text-sm leading-relaxed text-ink/80 [&_p]:mb-1.5 [&_strong]:font-mono [&_strong]:text-[13px] [&_strong]:font-medium [&_strong]:text-indigo-600 [&_code]:rounded [&_code]:bg-mist [&_code]:px-1 [&_code]:font-mono [&_code]:text-[12px]">
          <ReactMarkdown>{data.checklist}</ReactMarkdown>
        </div>
      </div>

      <aside className="h-fit rounded-2xl border border-line bg-white p-6 shadow-[0_18px_40px_-28px_rgba(91,33,182,0.5)]">
        <h3 className="font-display text-base font-bold">Why this order</h3>
        <p className="mt-1 text-xs text-ink/55">Files that more of the project imports come first.</p>
        <ul className="mt-4 space-y-4">
          {data.files.map((f, i) => (
            <li key={f.path}>
              <div className="break-all font-mono text-xs text-ink">{f.path}</div>
              <div className="mt-1.5 h-2 rounded-full bg-mist">
                <div className={`h-full rounded-full bg-gradient-to-r ${BAR[i % BAR.length]}`} style={{ width: `${(f.imported_by / max) * 100}%` }} />
              </div>
              <div className="mt-1 text-xs text-ink/55">imported by {f.imported_by} files, imports {f.imports}</div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

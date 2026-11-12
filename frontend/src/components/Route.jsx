const ICONS = {
  ingest: <path d="M12 4v10m0 0l-4-4m4 4l4-4M5 19h14" />,
  parse: <path d="M9 7l-5 5 5 5M15 7l5 5-5 5" />,
  graph: <path d="M6 7a2 2 0 100-4 2 2 0 000 4zM18 21a2 2 0 100-4 2 2 0 000 4zM18 7a2 2 0 100-4 2 2 0 000 4zM6 7v4a3 3 0 003 3h6M18 7v10" />,
  index: <path d="M11 18a7 7 0 100-14 7 7 0 000 14zM20 20l-4-4" />,
};

export default function Route({ steps, status }) {
  const done = steps.filter((s) => status[s.key] === "done").length;
  const running = steps.some((s) => status[s.key] === "running");
  const last = steps.length - 1;
  const fill = done >= 1 ? (done - 1) / last + (running ? 1 / (2 * last) : 0) : 0;

  return (
    <section
      aria-label="Analysis progress"
      className="rounded-2xl border border-white bg-white px-6 pb-7 pt-8 shadow-[0_24px_50px_-24px_rgba(91,33,182,0.55)]"
    >
      <div className="relative">
        <div className="absolute left-[12.5%] right-[12.5%] top-[21px] h-1 rounded bg-mist">
          <div
            className="h-full rounded bg-gradient-to-r from-sky-500 via-fuchsia-500 to-orange-400 transition-[width] duration-700 ease-out"
            style={{ width: `${Math.min(fill, 1) * 100}%` }}
          />
        </div>

        <ol className="relative grid grid-cols-4">
          {steps.map((s) => {
            const st = status[s.key];
            const active = st === "done" || st === "running";
            return (
              <li key={s.key} className="flex flex-col items-center text-center">
                <span
                  className="relative flex h-11 w-11 items-center justify-center rounded-2xl border-2 text-white transition-all duration-500"
                  style={
                    active
                      ? { background: `linear-gradient(135deg, ${s.from}, ${s.to})`, borderColor: "transparent", boxShadow: `0 10px 22px -8px ${s.to}` }
                      : { background: "#fff", borderColor: "#e3ddf6", color: s.to }
                  }
                >
                  {st === "running" && <span className="absolute inset-0 animate-ping rounded-2xl" style={{ background: s.to, opacity: 0.35 }} />}
                  {st === "done" ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 12.5l4.5 4.5L19 7.5" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="relative">
                      {ICONS[s.key]}
                    </svg>
                  )}
                </span>
                <span className={`mt-3 font-display text-sm font-bold ${st ? "text-ink" : "text-ink/55"}`}>{s.label}</span>
                <span className="mt-1 hidden max-w-[11rem] text-xs leading-snug text-ink/55 sm:block">{s.note}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

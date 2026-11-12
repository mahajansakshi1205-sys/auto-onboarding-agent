import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api";

const SUGGESTIONS = [
  ["What is the main entry point of this project?", "border-indigo-300 text-indigo-700 hover:bg-indigo-50"],
  ["How is the code organised?", "border-pink-300 text-pink-700 hover:bg-pink-50"],
  ["Where is the core logic?", "border-teal-300 text-teal-700 hover:bg-teal-50"],
];
const CHIP = [
  "border-indigo-200 bg-indigo-50 text-indigo-700", "border-pink-200 bg-pink-50 text-pink-700",
  "border-teal-200 bg-teal-50 text-teal-700", "border-orange-200 bg-orange-50 text-orange-700",
  "border-sky-200 bg-sky-50 text-sky-700", "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-700",
];

export default function Chat({ repoId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => setMessages([]), [repoId]);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, loading]);

  async function send(text) {
    const question = text.trim();
    if (!question || loading) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(repoId, question, history);
      setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: err.message, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[600px] flex-col overflow-hidden rounded-2xl border border-line bg-white shadow-[0_18px_40px_-28px_rgba(249,115,22,0.55)]">
      <div className="bg-gradient-to-r from-orange-500 via-pink-500 to-fuchsia-500 px-6 py-4">
        <h3 className="font-display text-lg font-bold text-white">Ask about any part of the code</h3>
        <p className="text-sm text-white/85">Every answer links back to the files and lines it came from.</p>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto bg-gradient-to-b from-orange-50/40 to-white p-6">
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map(([s, c]) => (
              <button key={s} onClick={() => send(s)} className={`rounded-full border bg-white px-4 py-2 text-sm font-medium transition ${c}`}>
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[80%] rounded-2xl rounded-br-md bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2.5 text-sm text-white shadow-md shadow-indigo-300/50">
                {m.content}
              </p>
            </div>
          ) : (
            <div key={i} className={`max-w-[92%] rounded-2xl rounded-tl-md border p-4 ${m.error ? "border-rose-200 bg-rose-50" : "border-line bg-white shadow-sm"}`}>
              <div className={`text-sm leading-relaxed [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_code]:rounded [&_code]:bg-mist [&_code]:px-1 [&_code]:font-mono [&_code]:text-[12px] [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-mist [&_pre]:p-3 ${m.error ? "text-rose-700" : "text-ink/85"}`}>
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
              {m.sources?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {m.sources.map((s, k) => (
                    <span key={s.ref} title={s.name} className={`rounded-md border px-2 py-0.5 font-mono text-[11px] ${CHIP[k % CHIP.length]}`}>
                      <b>{s.ref}</b> {s.path}:{s.start_line}-{s.end_line}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        )}

        {loading && <p className="animate-pulse text-sm text-ink/45">Reading the code…</p>}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-3 border-t border-line bg-white p-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="Your question"
          placeholder="Ask a question about the code"
          className="min-w-0 flex-1 rounded-xl border border-line px-4 py-2.5 text-sm focus:border-pink-400 focus:outline-none"
        />
        <button type="submit" disabled={loading} className="rounded-xl bg-gradient-to-r from-orange-500 to-pink-500 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-pink-300/60 transition hover:brightness-110 disabled:opacity-60">
          Ask
        </button>
      </form>
    </div>
  );
}

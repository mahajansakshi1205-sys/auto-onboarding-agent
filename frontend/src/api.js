export const BASE = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const post = (path, body) =>
  request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export const api = {
  health: () => request("/health"),
  ingest: (url) => post("/repos/ingest", { repo_url: url }),
  parse: (id) => post(`/repos/${id}/parse`),
  buildGraph: (id) => post(`/repos/${id}/graph/build`),
  index: (id) => post(`/repos/${id}/index`),
  analytics: (id, top = 10) => request(`/repos/${id}/analytics?top=${top}`),
  map: (id) => request(`/repos/${id}/map`),
  impact: (id, fileId) => request(`/repos/${id}/impact/${fileId}`),
  checklist: (id, top = 8) => request(`/repos/${id}/checklist?top=${top}`),
  explain: (id, question) => post(`/repos/${id}/explain`, { question }),
  chat: (id, message, history) => post(`/repos/${id}/chat`, { message, history }),
};

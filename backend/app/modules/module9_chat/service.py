from groq import Groq

from app.config import settings
from app.modules.module6_explain.service import retrieve

SYSTEM_PROMPT = (
    "You are a helpful senior engineer answering questions about one codebase. "
    "Answer ONLY from the code chunks provided in the latest message. "
    "Cite sources like [1], [2]. "
    "If the chunks do not contain the answer, say you cannot tell from the indexed code. "
    "Keep answers short and in simple language. Use earlier messages only to understand follow-up questions."
)

MAX_HISTORY = 6  # last 6 messages are enough


def chat(repo_id: int, message: str, history: list, k: int = 6):
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is missing in .env")

    chunks = retrieve(repo_id, message, k)
    if not chunks:
        return {"answer": "I could not find relevant code for that question.", "sources": []}

    context = "\n\n".join(
        f"[{i}] {c['path']}:{c['start_line']}-{c['end_line']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-MAX_HISTORY:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": f"Question: {message}\n\nCode chunks:\n{context}"})

    llm = Groq(api_key=settings.groq_api_key)
    resp = llm.chat.completions.create(
        model=settings.groq_model, temperature=0.2, messages=messages
    )
    sources = [
        {"ref": i, "path": c["path"], "start_line": c["start_line"],
         "end_line": c["end_line"], "name": c.get("name")}
        for i, c in enumerate(chunks, 1)
    ]
    return {"answer": resp.choices[0].message.content, "sources": sources}
from groq import Groq
from app.config import settings
from app.modules.module5_rag.service import _get_model, _get_client

SYSTEM_PROMPT = (
    "You are a senior engineer onboarding a new developer. "
    "Answer ONLY using the code chunks provided. "
    "Cite every claim like [1] or [2]. "
    "If the chunks do not contain the answer, say you cannot tell from the indexed code. "
    "Explain in simple language."
)


def retrieve(repo_id: int, question: str, k: int = 6):
    model = _get_model()
    client = _get_client()
    collection = client.get_collection(f"repo_{repo_id}")
    emb = model.encode([question], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=emb, n_results=k + 4)

    chunks = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        path = meta.get("path", "")
        if path.startswith(("tests/", "docs/", "examples/")):
            continue  # skip tests/docs, we want the real code
        chunks.append({"text": doc, **meta})
    return chunks[:k]


def explain(repo_id: int, question: str, k: int = 6):
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is missing in .env")

    chunks = retrieve(repo_id, question, k)
    if not chunks:
        return {"question": question, "answer": "No relevant code found.", "sources": []}

    context = "\n\n".join(
        f"[{i}] {c['path']}:{c['start_line']}-{c['end_line']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    user_msg = f"Question: {question}\n\nCode chunks:\n{context}"

    llm = Groq(api_key=settings.groq_api_key)
    resp = llm.chat.completions.create(
        model=settings.groq_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    sources = [
        {"ref": i, "path": c["path"], "start_line": c["start_line"],
         "end_line": c["end_line"], "name": c.get("name")}
        for i, c in enumerate(chunks, 1)
    ]
    return {"question": question, "answer": resp.choices[0].message.content, "sources": sources}
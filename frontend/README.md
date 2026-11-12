# AI-Powered Auto-Onboarding Agent ("Explain My Codebase")

> Paste a GitHub repository link and get the files that matter, the order to read them in, what breaks when you change a file, and answers that point to the exact lines of code.

Built with **Retrieval-Augmented Generation (RAG)** on top of real static analysis, so the AI explains verified code instead of guessing.

## The problem

A new developer joining a project faces hundreds of files and no map. Reading everything is slow, and asking a plain chatbot about the code often gives invented answers. This project analyses the repository first, and only then lets an LLM explain what it found, with citations.

## What it does

| Feature | What you get |
|---|---|
| **Key files** | Importance ranking (PageRank, fan-in, size) with stat cards and a bar chart |
| **Code map** | Interactive dependency graph: zoom, drag, click a file to see who depends on it |
| **Impact analysis** | "If you change this file, N files may be affected" (direct and indirect) |
| **Architecture health** | Circular imports, heavily coupled files, files with no links |
| **Reading order** | AI-written onboarding checklist, ranked for a newcomer |
| **Ask the code** | Chat with history; every answer cites `file:start_line-end_line` |
| **Explain this file** | One click, plain-language explanation of any file on the map |

## Where Generative AI is used

1. **Indexing:** every function and class becomes one chunk, converted to a 384-number embedding (`all-MiniLM-L6-v2`) and stored in ChromaDB.
2. **Retrieval:** a question is embedded and the closest chunks are fetched (tests, docs and examples are filtered out).
3. **Generation:** an LLM (Groq, `openai/gpt-oss-120b`) writes the explanation, checklist or chat answer **only from those chunks**, citing them as [1], [2].
4. **Grounding:** if the evidence is thin, the answer says so instead of inventing details.

The dependency graph, ranking, impact analysis and health checks use no LLM: they are plain Python (`ast`, NetworkX, Pandas, NumPy).

## Architecture

```
React dashboard  ->  FastAPI routers  ->  Services (modules 1 to 10)  ->  SQLite | ChromaDB | cloned repos
                                                        |-> GitHub (git clone)
                                                        |-> Groq LLM API
```

Pipeline: **Clone -> Parse -> Map -> Index**, then every tab reads from the stored results.

## Modules

| # | Module | Job |
|---|---|---|
| 1 | Ingestion | Shallow-clone the repo, catalogue files (path, size, lines) |
| 2 | Parser | Python `ast`: functions, classes, imports, docstrings |
| 3 | Dependency graph | Resolve imports into file-to-file edges (NetworkX) |
| 4 | Analytics | PageRank, fan-in/out, importance score, bar chart |
| 5 | Semantic search | Embeddings + ChromaDB, one collection per repository |
| 6 | Explain | RAG answer with citations |
| 7 | Diagram | Mermaid architecture diagram (top files) |
| 8 | Checklist | Ordered reading list written by the LLM |
| 9 | Chat | Multi-turn Q&A, last 6 turns of history |
| 10 | Insights | Code map data, impact analysis, architecture health |

## Tech stack

**Backend:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy 2, SQLite, GitPython, `ast`, NetworkX, Pandas, NumPy, Matplotlib, sentence-transformers, ChromaDB, Groq SDK

**Frontend:** React 19, Vite, Tailwind CSS v4, d3-force, react-markdown

**Testing:** pytest, FastAPI TestClient, pytest-cov

## Project layout

```
auto-onboarding-agent/
├── backend/
│   ├── app/
│   │   ├── main.py            app, CORS, routers
│   │   ├── config.py          settings from .env
│   │   ├── db.py              database session
│   │   ├── routers/           HTTP layer
│   │   └── modules/           module1_ingestion ... module10_insights
│   ├── tests/                 pytest suites
│   ├── data/                  database, vectors, cloned repos (gitignored)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx  api.js  index.css
│       └── components/        Route, Dashboard, Overview, CodeMap, Checklist, Chat
└── README.md
```

## Getting started

You need Python 3.11+, Node.js (LTS) and a free [Groq API key](https://console.groq.com).

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Open `.env` and set `GROQ_API_KEY`. Then start the server:

```powershell
uvicorn app.main:app --reload --reload-dir app
```

API docs: http://127.0.0.1:8000/docs

> The first run downloads the embedding model, so the first indexing takes a few minutes. Later runs are fast.

### 2. Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, paste a public GitHub URL such as `https://github.com/pallets/flask`, and press **Analyze repository**.

## Configuration (`backend/.env`)

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM key (required for explain, checklist and chat) |
| `GROQ_MODEL` | Model name, default `openai/gpt-oss-120b` |
| `GITHUB_TOKEN` | Optional, for rate limits or private repos |
| `DATABASE_URL` | Default `sqlite:///./data/app.db` |

Changes to `.env` need a full server restart.

## Main API endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/repos/{id}/analytics/chart` | Importance bar chart (PNG) |
| POST | `/repos/{id}/explain` | Grounded explanation with sources |
| GET | `/repos/{id}/diagram` | Mermaid diagram (plain text) |
| GET | `/repos/{id}/checklist` | Reading order and file stats |
| POST | `/repos/{id}/chat` | Answer and cited sources |
| GET | `/repos/{id}/map` | Graph nodes, edges, health, stats |
| GET | `/repos/{id}/impact/{file_id}` | Direct and indirect impact |

All routes are listed at `/docs`.

## Testing

```powershell
cd backend
pip install pytest httpx pytest-cov
pytest tests -v
```

30 automated tests cover Module 10 (file rules, dependency map, cycle detection, impact analysis, HTTP layer). The service has 100% statement coverage, and a mutation check (15 deliberately injected bugs) is caught by the tests. Modules 1 to 9 were tested end to end on `pallets/flask` and on this author's own repository.




## Limitations

- Python repositories only (the parser uses Python `ast`).
- Public repositories by default.
- Answers depend on the retrieved chunks; repositories with few docstrings give shorter explanations.
- Automated tests cover Module 10; modules 1 to 9 are checked manually.

## Author

Sakshi Mahajan, B.Tech Computer Science, Medicaps University, Indore.

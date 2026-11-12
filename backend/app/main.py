from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers import health, ingestion, parsing, graph, analytics,rag, explain, diagram ,checklist,chat,insights
from app.routers import explain

app = FastAPI(title="AI-Powered Auto-Onboarding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(parsing.router)
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(rag.router)
app.include_router(explain.router)
app.include_router(diagram.router)
app.include_router(checklist.router)
app.include_router(chat.router)
app.include_router(insights.router)
@app.get("/")
def root():
    return {"message": "AI-Powered Auto-Onboarding Agent API"}
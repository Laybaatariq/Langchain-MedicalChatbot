from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, health
from app.db.mongo import ensure_indexes
from app.rag.vector_store import ensure_collection_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at server startup. Failures are logged, not fatal, so a flaky
    # network doesn't stop the whole server from starting.
    try:
        ensure_collection_exists()
    except Exception as exc:
        print(f"[startup] Qdrant collection check failed: {exc}")

    try:
        ensure_indexes()
    except Exception as exc:
        print(f"[startup] MongoDB index setup failed: {exc}")

    yield


app = FastAPI(
    title="Medical Chatbot API",
    description="A LangChain + RAG powered medical information chatbot (portfolio project).",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS: allows the React frontend (running on a different port) to call this API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routes ---
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "Medical Chatbot API is running. See /docs for API documentation."}
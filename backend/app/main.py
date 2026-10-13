from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import accounts, booking, chat, health
from app.auth import users
from app.booking import repo as booking_repo
from app.db.mongo import ensure_indexes
from app.rag.vector_store import ensure_collection_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at server startup. Failures are logged, not fatal, so a flaky
    # network doesn't stop the whole server from starting.
    for name, task in [
        ("Qdrant collection check", ensure_collection_exists),
        ("MongoDB chat index", ensure_indexes),
        ("users index", users.ensure_indexes),
        ("appointments index", booking_repo.ensure_indexes),
    ]:
        try:
            task()
        except Exception as exc:
            print(f"[startup] {name} failed: {exc}")

    yield


app = FastAPI(
    title="Medical Chatbot API",
    description="A LangChain + RAG powered medical information chatbot (portfolio project).",
    version="0.3.0",
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
app.include_router(accounts.router)
app.include_router(booking.router)


@app.get("/")
async def root():
    return {"message": "Medical Chatbot API is running. See /docs for API documentation."}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, health

app = FastAPI(
    title="Medical Chatbot API",
    description="A LangChain + RAG powered medical information chatbot (portfolio project).",
    version="0.1.0",
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
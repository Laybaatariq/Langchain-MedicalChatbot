import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding

from app.core.config import get_settings

settings = get_settings()

# --- Embedding model (free, lightweight, no torch) ---
_embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
_EMBEDDING_DIM = 384  # output size of this model; must match the Qdrant collection


def _build_client() -> QdrantClient:
    """
    Cloud-only: connects to Qdrant Cloud using QDRANT_URL and QDRANT_API_KEY from .env.
    Fails early with a clear message if either is missing.
    """
    if not settings.qdrant_url or not settings.qdrant_api_key:
        raise RuntimeError(
            "QDRANT_URL and QDRANT_API_KEY must be set in backend/.env "
            "(Qdrant Cloud cluster URL and API key)."
        )

    print(f"[Qdrant] Connecting to cloud: {settings.qdrant_url}")
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )


_client = _build_client()


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a list of texts, returning plain Python lists."""
    return [vec.tolist() for vec in _embedding_model.embed(texts)]


def _embed_query(text: str) -> list[float]:
    """Embeds a single query string."""
    return list(_embedding_model.embed([text]))[0].tolist()


def check_connection() -> bool:
    """Returns True if the Qdrant Cloud cluster is reachable."""
    try:
        _client.get_collections()
        return True
    except Exception as exc:
        print(f"[Qdrant] Connection failed: {exc}")
        return False


def ensure_collection_exists() -> None:
    """Creates the collection if missing. Safe to call on every startup."""
    if not _client.collection_exists(settings.qdrant_collection_name):
        _client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(size=_EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {settings.qdrant_collection_name}")
    else:
        print(f"Collection '{settings.qdrant_collection_name}' already exists.")


def upsert_documents(texts: list[str], metadatas: list[dict] | None = None) -> None:
    """
    Embeds text chunks and stores them in Qdrant Cloud.
    Point IDs are derived from the content, so re-running ingestion
    updates existing chunks instead of duplicating them.
    """
    if metadatas is None:
        metadatas = [{} for _ in texts]

    vectors = _embed_texts(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{metadata.get('source', '')}:{text}")),
            vector=vector,
            payload={"text": text, **metadata},
        )
        for text, vector, metadata in zip(texts, vectors, metadatas)
    ]

    _client.upsert(collection_name=settings.qdrant_collection_name, points=points)
    print(f"Upserted {len(points)} chunks into Qdrant.")


def similarity_search(query: str, top_k: int = 4) -> list[dict]:
    """
    Returns the top_k most similar chunks:
    [{"text": ..., "score": ..., **metadata}]
    """
    response = _client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=_embed_query(query),
        limit=top_k,
    )

    return [
        {
            "text": hit.payload.get("text", ""),
            "score": hit.score,
            **{k: v for k, v in hit.payload.items() if k != "text"},
        }
        for hit in response.points
    ]


# --- Quick manual test ---
#   python -m app.rag.vector_store
if __name__ == "__main__":
    print("Checking Qdrant Cloud connection...")
    if not check_connection():
        raise SystemExit("Could not reach Qdrant Cloud. Check QDRANT_URL and QDRANT_API_KEY in .env.")

    ensure_collection_exists()

    print("\nUpserting a test document...")
    upsert_documents(
        texts=["Paracetamol is commonly used to reduce fever and relieve mild pain."],
        metadatas=[{"source": "test_doc"}],
    )

    print("\nRunning a test search...")
    for r in similarity_search("medicine for fever", top_k=1):
        print(f"- score={r['score']:.4f} | text={r['text']}")

    _client.close()
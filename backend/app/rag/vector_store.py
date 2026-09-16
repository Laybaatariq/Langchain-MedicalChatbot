from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from uuid import uuid5, NAMESPACE_URL

from app.core.config import get_settings

settings = get_settings()

# --- Embedding model (FREE, runs locally, no API key needed) ---
# "all-MiniLM-L6-v2" is a small, fast, well-regarded open-source model.
# It downloads once (~80MB) the first time you run this, then caches locally.
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
_EMBEDDING_DIM = 384  # this model's output vector size (must match Qdrant config)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a list of texts, returning plain Python lists (not numpy arrays)."""
    vectors = _embedding_model.encode(texts, convert_to_numpy=True)
    return vectors.tolist()


def _embed_query(text: str) -> list[float]:
    """Embeds a single query string."""
    return _embedding_model.encode(text, convert_to_numpy=True).tolist()


# --- Qdrant client (single shared instance) ---
_client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
)


def ensure_collection_exists() -> None:
    """
    Creates the Qdrant collection if it doesn't already exist.
    Safe to call every time the app starts — it checks first.
    """
    existing = [c.name for c in _client.get_collections().collections]

    if settings.qdrant_collection_name not in existing:
        _client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                size=_EMBEDDING_DIM,
                distance=Distance.COSINE,  # cosine similarity works well for text embeddings
            ),
        )
        print(f"Created Qdrant collection: {settings.qdrant_collection_name}")
    else:
        print(f"Collection '{settings.qdrant_collection_name}' already exists.")


def upsert_documents(
    texts: list[str],
    metadatas: list[dict] | None = None,
) -> None:
    """Embeds and uploads documents to Qdrant in small batches."""
    if metadatas is None:
        metadatas = [{} for _ in texts]

    if len(texts) != len(metadatas):
        raise ValueError("texts and metadatas must have the same length")

    vectors = _embed_texts(texts)
    batch_size = 64
    total_uploaded = 0

    for start in range(0, len(texts), batch_size):
        end = start + batch_size

        points = [
            PointStruct(
                id=str(uuid5(
                    NAMESPACE_URL,
                    f"{metadata.get('source', 'unknown')}:{start + offset}:{text}",
                )),
                vector=vector,
                payload={"text": text, **metadata},
            )
            for offset, (text, vector, metadata) in enumerate(
                zip(texts[start:end], vectors[start:end], metadatas[start:end])
            )
        ]

        _client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
        )

        total_uploaded += len(points)
        print(f"Uploaded {total_uploaded}/{len(texts)} chunks")

    print(f"Upserted {total_uploaded} chunks into Qdrant.")


def similarity_search(query: str, top_k: int = 4) -> list[dict]:
    """
    Embeds the user's query and retrieves the top_k most similar
    chunks from Qdrant. This is what medical_qa_chain.py will call
    to get grounding context before asking the LLM.

    Returns a list of dicts: [{"text": ..., "score": ..., **metadata}]
    """
    query_vector = _embed_query(query)

    results = _client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=query_vector,
        limit=top_k,
    )

    return [
        {
            "text": hit.payload.get("text", ""),
            "score": hit.score,
            **{k: v for k, v in hit.payload.items() if k != "text"},
        }
        for hit in results
    ]


# --- Quick manual test ---
# Run this file directly to sanity-check your Qdrant connection
# before wiring it into the rest of the app:
#   python -m app.rag.vector_store
if __name__ == "__main__":
    print("Checking Qdrant connection...")
    ensure_collection_exists()

    print("\nUpserting a test document...")
    upsert_documents(
        texts=["Paracetamol is commonly used to reduce fever and relieve mild pain."],
        metadatas=[{"source": "test_doc"}],
    )

    print("\nRunning a test search...")
    results = similarity_search("medicine for fever", top_k=1)
    for r in results:
        print(f"- score={r['score']:.4f} | text={r['text']}")
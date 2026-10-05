"""
Debug helper for the RAG pipeline (not used by the app itself).

  python -m app.rag.debug_search "symptoms of flu"          # top matches with scores
  python -m app.rag.debug_search --count                    # how many chunks are stored
  python -m app.rag.debug_search --sources                  # chunks per source
  python -m app.rag.debug_search --grep influenza           # is this word in the STORED chunks?
  python -m app.rag.debug_search --delete-source test_doc   # remove all chunks of one source
"""
import sys
from collections import Counter

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
)

from app.core.config import get_settings
from app.rag.vector_store import similarity_search

settings = get_settings()
COLLECTION = settings.qdrant_collection_name

# Own client, so this script doesn't depend on how vector_store.py creates its client
client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
    timeout=60,
)


def show_count() -> None:
    total = client.count(collection_name=COLLECTION, exact=True).count
    print(f"Collection: '{COLLECTION}'")
    print(f"Chunks stored: {total}")


def show_sources() -> None:
    """Counts chunks per source (all MedlinePlus topics are grouped into one line)."""
    print(f"Collection: '{COLLECTION}'")
    counts: Counter = Counter()
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=256,
            offset=offset,
            with_payload=["source"],
            with_vectors=False,
        )
        for point in points:
            source = point.payload.get("source", "unknown")
            key = "MedlinePlus (all topics)" if source.startswith("MedlinePlus:") else source
            counts[key] += 1
        if offset is None:
            break

    for name, number in counts.most_common():
        print(f"{number:6d}  {name}")


def search(query: str) -> None:
    print(f"Collection: '{COLLECTION}'")
    print(f"Query: {query}\n")
    for r in similarity_search(query, top_k=8):
        snippet = r["text"].replace("\n", " ")[:110]
        page = r.get("page", "-")
        print(f"{r['score']:.3f} | {r.get('source', '?')} p.{page} | {snippet}")


def grep(word: str) -> None:
    """Scans every stored chunk (fast, no PDF parsing) for a word."""
    word = word.lower()
    scanned = 0
    hits: list[tuple] = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            scanned += 1
            text = point.payload.get("text", "")
            if word in text.lower():
                hits.append((point.payload.get("source", "?"), text))
        if offset is None:
            break

    print(f"Scanned {scanned} chunks. '{word}' appears in {len(hits)} of them.")
    for source, text in hits[:5]:
        print(f"  - {source} | {text.replace(chr(10), ' ')[:110]}")


def delete_source(name: str) -> None:
    """Deletes every chunk whose 'source' equals `name` (e.g. Medical_book.pdf or test_doc)."""
    # Filtering on a field needs a payload index (Qdrant Cloud can refuse unindexed filters).
    # Creating it again when it already exists is harmless.
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="source",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    condition = Filter(must=[FieldCondition(key="source", match=MatchValue(value=name))])
    before = client.count(collection_name=COLLECTION, count_filter=condition, exact=True).count
    client.delete(collection_name=COLLECTION, points_selector=FilterSelector(filter=condition))
    print(f"Deleted {before} chunk(s) with source '{name}'.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "--count":
        show_count()
    elif args[0] == "--sources":
        show_sources()
    elif args[0] == "--grep" and len(args) > 1:
        grep(args[1])
    elif args[0] == "--delete-source" and len(args) > 1:
        delete_source(" ".join(args[1:]))
    elif args[0].startswith("--"):
        print(f"Unknown option: {args[0]}\n")
        print(__doc__)
    else:
        search(" ".join(args))
    client.close()

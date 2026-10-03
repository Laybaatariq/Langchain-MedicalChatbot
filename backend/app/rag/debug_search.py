"""
Debug helper for the RAG pipeline (not used by the app itself).

  python -m app.rag.debug_search "symptoms of flu"   # top matches with scores
  python -m app.rag.debug_search --count             # how many chunks are stored
  python -m app.rag.debug_search --grep influenza    # does the PDF text contain this word?
  python -m app.rag.debug_search --delete-test       # remove the old test_doc chunk
"""
import sys
import uuid

from pypdf import PdfReader
from qdrant_client.models import PointIdsList

from app.core.config import get_settings
from app.rag.ingest import DOCS_FOLDER
from app.rag.vector_store import _client, similarity_search

settings = get_settings()

TEST_TEXT = "Paracetamol is commonly used to reduce fever and relieve mild pain."


def show_count() -> None:
    total = _client.count(collection_name=settings.qdrant_collection_name, exact=True).count
    print(f"Chunks stored in '{settings.qdrant_collection_name}': {total}")


def search(query: str) -> None:
    print(f"Query: {query}\n")
    for r in similarity_search(query, top_k=8):
        snippet = r["text"].replace("\n", " ")[:110]
        page = r.get("page", "?")
        print(f"{r['score']:.3f} | {r.get('source', '?')} p.{page} | {snippet}")


def grep(word: str) -> None:
    word = word.lower()
    for pdf in sorted(DOCS_FOLDER.glob("*.pdf")):
        reader = PdfReader(str(pdf))
        total_pages = len(reader.pages)
        hits = []
        for number, page in enumerate(reader.pages, start=1):
            if number % 200 == 0:
                print(f"  ...scanned {number}/{total_pages} pages")
            if word in (page.extract_text() or "").lower():
                hits.append(number)
        print(f"{pdf.name}: {total_pages} pages, '{word}' found on {len(hits)} page(s), first: {hits[:8]}")


def delete_test() -> None:
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test_doc:{TEST_TEXT}"))
    _client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=PointIdsList(points=[point_id]),
    )
    print("Deleted the test_doc chunk (if it existed).")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "--count":
        show_count()
    elif args[0] == "--grep" and len(args) > 1:
        grep(args[1])
    elif args[0] == "--delete-test":
        delete_test()
    else:
        search(" ".join(args))
    _client.close()
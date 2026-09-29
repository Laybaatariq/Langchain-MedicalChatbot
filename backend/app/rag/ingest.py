from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.vector_store import ensure_collection_exists, upsert_documents

# --- Config for chunking ---
CHUNK_SIZE = 500       # characters per chunk (roughly ~100-125 tokens)
CHUNK_OVERLAP = 50     # overlap between chunks so context isn't lost at boundaries
MIN_CHUNK_CHARS = 40   # skip tiny fragments (page numbers, headers)
BATCH_SIZE = 64        # chunks embedded + uploaded per request

# Folder: backend/app/data/medical_docs/
DOCS_FOLDER = Path(__file__).resolve().parents[1] / "data" / "medical_docs"


def load_documents(folder: Path) -> list[dict]:
    """
    Loads every .txt and .pdf file in the given folder.
    Returns a list of dicts: [{"text": ..., "source": filename, "page": int | None}]
    PDFs produce one entry per page; .txt files produce one entry.
    """
    documents = []

    if not folder.exists():
        print(f"Folder not found: {folder}")
        return documents

    for file_path in sorted(folder.iterdir()):
        if not file_path.is_file():
            continue  # skip subfolders

        suffix = file_path.suffix.lower()  # normalize so .PDF / .Pdf / .pdf all match

        if suffix == ".txt":
            loader = TextLoader(str(file_path), encoding="utf-8")
        elif suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        else:
            continue  # skip unsupported file types

        loaded = loader.load()
        added = 0
        for doc in loaded:
            text = doc.page_content.strip()
            if not text:
                continue  # blank page (or scanned page with no text layer)

            # PyPDFLoader page numbers are 0-based; show them 1-based
            page = doc.metadata.get("page")
            documents.append({
                "text": text,
                "source": file_path.name,
                "page": page + 1 if isinstance(page, int) else None,
            })
            added += 1

        print(f"Loaded: {file_path.name} ({added} non-empty page(s)/section(s))")

    return documents


def chunk_documents(documents: list[dict]) -> tuple[list[str], list[dict]]:
    """
    Splits each document's text into overlapping chunks.
    Returns (texts, metadatas) - two parallel lists ready for upsert_documents().
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # tries paragraph breaks first, then sentences
    )

    texts = []
    metadatas = []

    for doc in documents:
        for chunk in splitter.split_text(doc["text"]):
            chunk = chunk.strip()
            if len(chunk) < MIN_CHUNK_CHARS:
                continue

            metadata = {"source": doc["source"]}
            if doc["page"] is not None:
                metadata["page"] = doc["page"]

            texts.append(chunk)
            metadatas.append(metadata)

    return texts, metadatas


def run_ingestion() -> None:
    """
    Main entry point: load -> chunk -> embed & store (in batches).
    Run this whenever you add new documents to data/medical_docs/.
    Safe to re-run: chunk IDs come from their content, so nothing is duplicated.
    """
    print(f"Looking for documents in: {DOCS_FOLDER}\n")

    documents = load_documents(DOCS_FOLDER)
    if not documents:
        print(
            "No readable text found. Add .txt or .pdf files to data/medical_docs/ first. "
            "(Scanned PDFs with no text layer need OCR.)"
        )
        return

    print(f"\nLoaded {len(documents)} page(s)/section(s). Splitting into chunks...")
    texts, metadatas = chunk_documents(documents)
    print(f"Created {len(texts)} chunks.")

    print("\nEnsuring Qdrant collection exists...")
    ensure_collection_exists()

    total = len(texts)
    print(f"Embedding and uploading in batches of {BATCH_SIZE}...")
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        upsert_documents(texts[start:end], metadatas[start:end])
        print(f"  Progress: {end}/{total} chunks")

    print("\nIngestion complete.")


# Run this file directly to index whatever is in data/medical_docs/:
#   python -m app.rag.ingest
if __name__ == "__main__":
    run_ingestion()
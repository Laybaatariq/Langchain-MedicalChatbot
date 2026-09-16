import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader

from app.rag.vector_store import ensure_collection_exists, upsert_documents

# --- Config for chunking ---
CHUNK_SIZE = 500       # characters per chunk (roughly ~100-125 tokens)
CHUNK_OVERLAP = 50     # overlap between chunks so context isn't lost at boundaries

# Folder: backend/app/data/medical_docs/
DOCS_FOLDER = Path(__file__).resolve().parents[1] / "data" / "medical_docs"


def load_documents(folder: Path) -> list[dict]:
    """
    Loads every .txt and .pdf file in the given folder.
    Returns a list of dicts: [{"text": ..., "source": filename}]
    """
    documents = []

    if not folder.exists():
        print(f"⚠️  Folder not found: {folder}")
        return documents

    for file_path in folder.iterdir():
        suffix = file_path.suffix.lower()  # normalize so .PDF / .Pdf / .pdf all match

        if not file_path.is_file():
            continue  # skip subfolders

        if suffix == ".txt":
            loader = TextLoader(str(file_path), encoding="utf-8")
        elif suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        else:
            continue  # skip unsupported file types

        loaded = loader.load()
        for doc in loaded:
            documents.append({
                "text": doc.page_content,
                "source": file_path.name,
            })

        print(f"Loaded: {file_path.name}")

    return documents


def chunk_documents(documents: list[dict]) -> tuple[list[str], list[dict]]:
    """
    Splits each document's text into overlapping chunks.
    Returns (texts, metadatas) — two parallel lists ready for upsert_documents().
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # tries paragraph breaks first, then sentences
    )

    texts = []
    metadatas = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({"source": doc["source"]})

    return texts, metadatas


def run_ingestion() -> None:
    """
    Main entry point: load -> chunk -> embed & store.
    Run this whenever you add new documents to data/medical_docs/.
    """
    print(f"Looking for documents in: {DOCS_FOLDER}\n")

    documents = load_documents(DOCS_FOLDER)
    if not documents:
        print("No documents found. Add .txt or .pdf files to data/medical_docs/ first.")
        return

    print(f"\nLoaded {len(documents)} document(s). Splitting into chunks...")
    texts, metadatas = chunk_documents(documents)
    print(f"Created {len(texts)} chunks.")

    print("\nEnsuring Qdrant collection exists...")
    ensure_collection_exists()

    print("Embedding and uploading chunks to Qdrant...")
    upsert_documents(texts, metadatas)

    print("\nIngestion complete.")


# Run this file directly to index whatever is in data/medical_docs/:
#   python -m app.rag.ingest
if __name__ == "__main__":
    run_ingestion()
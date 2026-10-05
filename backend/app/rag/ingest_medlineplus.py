"""
Loads MedlinePlus health topics (NIH, written for patients) into Qdrant.

1. Download the Health Topic XML (see the steps in the chat) to:
     backend/app/data/medlineplus/mplus_topics.xml
2. Run:
     python -m app.rag.ingest_medlineplus

Only English topics are loaded. Each topic becomes one chunk (long topics are split),
and every chunk starts with the topic title and its "also called" names, so searches
like "flu" or "influenza" both find the right topic.
"""
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

XML_PATH = Path(__file__).resolve().parents[1] / "data" / "medlineplus" / "mplus_topics.xml"

MAX_CHARS = 1200       # topics longer than this are split into several chunks
OVERLAP = 100
BATCH_SIZE = 64        # chunks embedded + uploaded per request

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHARS,
    chunk_overlap=OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def html_to_text(raw: str) -> str:
    """Turns the summary HTML into plain text, keeping paragraph breaks and bullets."""
    raw = re.sub(r"(?i)<li[^>]*>", "\n- ", raw)
    raw = re.sub(r"(?i)</(p|ul|ol|h\d)>|<br\s*/?>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_topics(xml_path: Path) -> list[dict]:
    """Returns [{"title", "url", "also_called", "group", "summary"}] for English topics."""
    root = ET.parse(xml_path).getroot()
    topics = []

    for topic in root.iter("health-topic"):
        if topic.get("language") != "English":
            continue

        summary_el = topic.find("full-summary")
        if summary_el is None:
            continue
        # The summary is HTML. It may arrive as escaped text or as real child elements,
        # so rebuild the raw HTML from both before converting it to plain text.
        raw_html = (summary_el.text or "") + "".join(
            ET.tostring(child, encoding="unicode") for child in summary_el
        )
        summary = html_to_text(raw_html)
        if not summary:
            continue

        groups = [g.text.strip() for g in topic.findall("group") if g.text]
        topics.append({
            "title": (topic.get("title") or "").strip(),
            "url": topic.get("url"),
            "also_called": [a.text.strip() for a in topic.findall("also-called") if a.text],
            "group": groups[0] if groups else None,
            "summary": summary,
        })

    return topics


def build_chunks(topics: list[dict]) -> tuple[list[str], list[dict]]:
    texts: list[str] = []
    metadatas: list[dict] = []

    for t in topics:
        header = t["title"]
        if t["also_called"]:
            header += f" (also called: {', '.join(t['also_called'])})"

        pieces = [t["summary"]] if len(t["summary"]) <= MAX_CHARS else _splitter.split_text(t["summary"])

        for piece in pieces:
            texts.append(f"{header}\n\n{piece.strip()}")
            metadata = {"source": f"MedlinePlus: {t['title']}", "title": t["title"]}
            if t["url"]:
                metadata["url"] = t["url"]
            if t["group"]:
                metadata["group"] = t["group"]
            metadatas.append(metadata)

    return texts, metadatas


def run_ingestion() -> None:
    # Imported here so the parsing functions above can be used without a Qdrant connection
    from app.rag.vector_store import ensure_collection_exists, upsert_documents

    if not XML_PATH.exists():
        print(f"File not found: {XML_PATH}")
        print("Download the MedlinePlus Health Topic XML first and save it with that name.")
        return

    print(f"Reading {XML_PATH.name} ...")
    topics = parse_topics(XML_PATH)
    texts, metadatas = build_chunks(topics)
    print(f"{len(topics)} English topics -> {len(texts)} chunks.")

    ensure_collection_exists()

    total = len(texts)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        upsert_documents(texts[start:end], metadatas[start:end])
        print(f"  Progress: {end}/{total} chunks")

    print("\nIngestion complete. Information from MedlinePlus.gov (National Library of Medicine).")


# python -m app.rag.ingest_medlineplus
if __name__ == "__main__":
    run_ingestion()

import glob
import hashlib
import os

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

DATA_DIR = "data"
DB_DIR = "chroma_db"
COLLECTION = "it_kb"


def doc_type_for(name: str) -> str:
    n = name.lower()
    if "runbook" in n:
        return "runbook"
    if "policy" in n:
        return "policy"
    if "standard" in n or "change" in n:
        return "standard"
    if "guide" in n or "ticketing" in n:
        return "guide"
    if "sop" in n or "onboarding" in n:
        return "sop"
    return "document"


def load_chunks():
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")], strip_headers=False
    )
    chunker = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)

    docs, ids = [], []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.md"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            text = f.read()

        sections = header_splitter.split_text(text)
        chunks = chunker.split_documents(sections)
        for i, ch in enumerate(chunks):
            section = ch.metadata.get("section", "Intro")
            ch.metadata = {
                "source": name,
                "section": section,
                "doc_type": doc_type_for(name),
            }
            # Deterministic ID -> re-running updates instead of duplicating
            raw = f"{name}|{section}|{i}"
            ids.append(hashlib.sha1(raw.encode()).hexdigest())
            docs.append(ch)
    return docs, ids


def main():
    docs, ids = load_chunks()
    if not docs:
        raise SystemExit("No .md files found in ./data")

    vs = Chroma(
        collection_name=COLLECTION,
        embedding_function=OllamaEmbeddings(model="nomic-embed-text"),
        persist_directory=DB_DIR,
    )
    vs.add_documents(docs, ids=ids)  # upsert by id
    total = vs._collection.count()
    print(f"Ingested {len(docs)} chunks from {len(set(d.metadata['source'] for d in docs))} files.")
    print(f"Collection now holds {total} chunks (run again: this number must NOT grow).")


if __name__ == "__main__":
    main()
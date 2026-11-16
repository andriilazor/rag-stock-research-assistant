import re
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from config import OLLAMA_URL, EMBED_MODEL, INDEX_DIR

CHUNK_SIZE = 800

# splits the report into its metadata block
def read_report(path):
    _, header, body = path.read_text().split("---", 2)
    metadata = dict(line.split(": ", 1) for line in header.strip().splitlines())
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL) # here we removing hidden HTML comments
    return metadata, body.strip()
  
# group paragraphs into chunks
def split_text(text):
    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        if current and len(current) + len(paragraph) > CHUNK_SIZE:
            chunks.append(current.strip())
            current = ""
        current += paragraph + "\n\n"
    chunks.append(current.strip())
    return chunks
  
texts, metadatas = [], []
for path in sorted(Path("data/reports").glob("*.md")):
    meta, body = read_report(path)
    for chunk in split_text(body):
        # the first line tells which company and document the chunk comes from for more context.
        texts.append(f"{meta['company']} ({meta['ticker']}), {meta['doc_type']}, {meta['date']}\n{chunk}")
        metadatas.append(
            {"ticker": meta["ticker"], "doc_type": meta["doc_type"], "date": meta["date"], "source": path.name}
        )

embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
index = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
index.save_local(INDEX_DIR)
print(f"Indexed {len(texts)} chunks from {len(set(m['source'] for m in metadatas))} files")
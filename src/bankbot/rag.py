"""RAG: split policy docs into chunks -> embed -> store in Chroma -> retrieve by question."""
import hashlib
import math
import re

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

from . import config


class _HashEmbeddings(Embeddings):
    """Fake embeddings for tests: hash words into 256 dimensions (bag of words). No model download; crude but reproducible."""

    def _vec(self, text: str):
        v = [0.0] * 256
        for w in re.findall(r"[a-z0-9$%]+", text.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class _ChromaDefaultEmbeddings(Embeddings):
    """Use Chroma's built-in local model (all-MiniLM-L6-v2, ONNX, ~80MB, downloaded automatically on first run, no key needed)."""

    def __init__(self):
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        self._fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts):
        return [list(map(float, v)) for v in self._fn(texts)]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def get_embeddings() -> Embeddings:
    return _HashEmbeddings() if config.EMBEDDINGS == "fake" else _ChromaDefaultEmbeddings()


def load_chunks(policy_dir=None):
    """Read each markdown file, split into chunks by heading (# / ##), and record the source filename and heading."""
    policy_dir = policy_dir or config.POLICY_DIR
    splitter = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2")], strip_headers=False)
    chunks = []
    for path in sorted(policy_dir.glob("*.md")):
        for doc in splitter.split_text(path.read_text(encoding="utf-8")):
            doc.metadata["source"] = path.name
            chunks.append(doc)
    return chunks


def build_index(policy_dir=None, persist_dir=None, embeddings=None) -> Chroma:
    """(Re)build the index. Run again whenever the docs change."""
    persist_dir = str(persist_dir or config.CHROMA_DIR)
    store = Chroma(collection_name="policies", embedding_function=embeddings or get_embeddings(),
                   persist_directory=persist_dir)
    store.reset_collection()
    store.add_documents(load_chunks(policy_dir))
    return store


def get_store(persist_dir=None, embeddings=None) -> Chroma:
    return Chroma(collection_name="policies", embedding_function=embeddings or get_embeddings(),
                  persist_directory=str(persist_dir or config.CHROMA_DIR))


def search(store: Chroma, query: str, k: int = 3):
    return store.similarity_search(query, k=k)

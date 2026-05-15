"""Vector retriever backed by ChromaDB and multilingual E5 embeddings."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import get_cached_settings
    from src.utils.citation import vector_citation_from_metadata
    from src.utils.chroma_compat import disable_chromadb_default_onnx
    from src.utils.language_detect import detect_language
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings
    from backend.src.utils.citation import vector_citation_from_metadata
    from backend.src.utils.chroma_compat import disable_chromadb_default_onnx
    from backend.src.utils.language_detect import detect_language

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorDocument:
    """One vector retrieval hit."""

    doc_id: str
    text: str
    metadata: dict[str, Any]
    distance: float


@dataclass(frozen=True)
class VectorRetrievalResult:
    """Vector retrieval result."""

    strategy: str
    language: str
    query: str
    documents: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    fallback_signal: str | None


class E5QueryEmbedder:
    """Query embedder for multilingual E5."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Package sentence-transformers belum terpasang") from exc
        self.model = SentenceTransformer(model_name)

    def embed_query(self, query: str) -> list[float]:
        """Embed query with the E5 query prefix."""
        embedding = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return embedding.tolist()


class VectorRetriever:
    """Search ChromaDB retrieval documents."""

    def __init__(self, collection_name: str | None = None) -> None:
        settings = get_cached_settings()
        self.settings = settings
        self.collection_name = collection_name or settings.chroma_collection_name
        self.client: Any | None = None
        self.collection: Any | None = None
        self.embedder: E5QueryEmbedder | None = None
        self.unavailable_reason: str | None = None
        self.lexical_documents = self.load_lexical_documents()
        if os.getenv("VECTOR_RETRIEVAL_MODE", "auto").strip().lower() == "lexical":
            self.unavailable_reason = "Vector retrieval memakai lexical fallback lokal."
            return
        disable_chromadb_default_onnx()
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Package chromadb belum terpasang") from exc
        try:
            self.client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
            self.collection = self.client.get_or_create_collection(
                self.collection_name,
                embedding_function=None,
            )
        except Exception as exc:
            self.unavailable_reason = f"Vector store tidak tersedia: {exc}"
            LOGGER.warning(self.unavailable_reason)
        try:
            self.embedder = E5QueryEmbedder(settings.embedding_model_name)
        except Exception as exc:
            self.unavailable_reason = f"Embedding model tidak tersedia: {exc}"
            LOGGER.warning(self.unavailable_reason)

    def load_lexical_documents(self) -> list[dict[str, Any]]:
        """Load JSONL retrieval documents for local lexical fallback."""
        path = self.settings.processed_data_dir / "documents.jsonl"
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def lexical_retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Search local documents with a lightweight token overlap fallback."""
        tokens = {
            token
            for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", query.lower())
            if len(token) > 2
            and token
            not in {
                "dan",
                "atau",
                "yang",
                "untuk",
                "profil",
                "profile",
                "valuasi",
                "valuasinya",
                "nilai",
                "pasar",
                "pemain",
                "player",
                "tentang",
            }
        }
        if not tokens:
            return []
        scored: list[tuple[float, dict[str, Any]]] = []
        for document in self.lexical_documents:
            text = str(document.get("text") or "")
            metadata = dict(document.get("metadata") or {})
            player_name = str(metadata.get("player_name", "")).lower()
            haystack = f"{player_name} {metadata.get('club', '')} {metadata.get('league', '')} {text}".lower()
            score = sum(4.0 if token in str(metadata.get("player_name", "")).lower() else 1.0 for token in tokens if token in haystack)
            if player_name and re.search(rf"\b{re.escape(player_name)}\b", query.lower()):
                score += 20.0
            if score:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, document in scored[:top_k]:
            results.append(
                {
                    "doc_id": str(document.get("doc_id")),
                    "text": str(document.get("text") or ""),
                    "metadata": dict(document.get("metadata") or {}),
                    "distance": 1.0 / (score + 1.0),
                }
            )
        return results

    def retrieve(self, query: str, top_k: int = 5) -> VectorRetrievalResult:
        """Search vector documents."""
        language = detect_language(query)
        if self.collection is None or self.embedder is None:
            documents = self.lexical_retrieve(query, top_k)
            citations = [
                vector_citation_from_metadata(document["metadata"], document["doc_id"]).to_dict()
                for document in documents
            ]
            return VectorRetrievalResult(
                strategy="vector_only",
                language=language,
                query=query,
                documents=documents,
                citations=citations,
                fallback_signal=None if documents else self.unavailable_reason or "Vector store tidak tersedia.",
            )
        query_embedding = self.embedder.embed_query(query)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        texts = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        documents: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for index, doc_id in enumerate(ids):
            metadata = dict(metadatas[index] or {})
            document = VectorDocument(
                doc_id=str(doc_id),
                text=str(texts[index]),
                metadata=metadata,
                distance=float(distances[index]),
            )
            documents.append(asdict(document))
            citations.append(vector_citation_from_metadata(metadata, str(doc_id)).to_dict())
        return VectorRetrievalResult(
            strategy="vector_only",
            language=language,
            query=query,
            documents=documents,
            citations=citations,
            fallback_signal=None if documents else "Data tidak tersedia dalam sistem.",
        )


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    parser = argparse.ArgumentParser(description="Smoke test vector retriever")
    parser.add_argument("--query", default="Profil Aaron Ramsdale dan valuasinya")
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> None:
    """CLI entry point."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    args = build_arg_parser().parse_args()
    result = VectorRetriever().retrieve(args.query, top_k=args.top_k)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

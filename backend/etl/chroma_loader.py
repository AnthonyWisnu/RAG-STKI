"""Load generated retrieval documents into ChromaDB."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import get_cached_settings
    from etl.neo4j_loader import chunked
    from src.utils.chroma_compat import disable_chromadb_default_onnx
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings
    from backend.etl.neo4j_loader import chunked
    from backend.src.utils.chroma_compat import disable_chromadb_default_onnx
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChromaLoadSummary:
    """Ringkasan hasil upsert ChromaDB."""

    collection_name: str
    document_count: int
    persisted_path: Path


class E5Embedder:
    """SentenceTransformer wrapper untuk model E5 multilingual."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Package sentence-transformers belum terpasang") from exc
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embed document passages with E5 passage prefix."""
        prefixed = [f"passage: {text}" for text in texts]
        embeddings = self.model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed query with E5 query prefix."""
        embedding = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return embedding.tolist()


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Load generated retrieval documents JSONL."""
    documents: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            documents.append(json.loads(line))
            if limit is not None and len(documents) >= limit:
                break
    return documents


class ChromaDocumentLoader:
    """Idempotent ChromaDB upsert untuk retrieval documents."""

    def __init__(
        self,
        collection_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        settings = get_cached_settings()
        settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        disable_chromadb_default_onnx()
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Package chromadb belum terpasang") from exc

        self.persist_path = settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = E5Embedder(model_name or settings.embedding_model_name)

    def upsert_documents(
        self,
        documents: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> ChromaLoadSummary:
        """Upsert documents into ChromaDB with deterministic IDs."""
        settings = get_cached_settings()
        actual_batch_size = batch_size or settings.document_batch_size
        total = 0
        for batch in chunked(documents, actual_batch_size):
            ids = [str(document["doc_id"]) for document in batch]
            texts = [str(document["text"]) for document in batch]
            metadatas = [document["metadata"] for document in batch]
            embeddings = self.embedder.embed_passages(texts)
            self.collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            total += len(batch)
            LOGGER.info("Upserted Chroma batch: %s total=%s", len(batch), total)
        return ChromaLoadSummary(
            collection_name=self.collection_name,
            document_count=total,
            persisted_path=self.persist_path,
        )

    def similarity_search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Run a simple similarity search against the collection."""
        query_embedding = self.embedder.embed_query(query)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        rows: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for index, doc_id in enumerate(ids):
            rows.append(
                {
                    "doc_id": doc_id,
                    "distance": distances[index],
                    "metadata": metadatas[index],
                    "text": documents[index],
                }
            )
        return rows


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    settings = get_cached_settings()
    parser = argparse.ArgumentParser(description="Load retrieval documents into ChromaDB")
    parser.add_argument(
        "--input",
        type=Path,
        default=settings.processed_data_dir / "documents.jsonl",
        help="Input JSONL dari document_generator.py",
    )
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah dokumen untuk smoke test")
    parser.add_argument("--batch-size", type=int, default=None, help="Ukuran batch upsert")
    parser.add_argument("--collection", default=None, help="Nama collection Chroma")
    parser.add_argument("--model", default=None, help="SentenceTransformer model name")
    parser.add_argument("--smoke-test", action="store_true", help="Jalankan similarity search setelah upsert")
    parser.add_argument("--query", default="Premier League goalkeeper saves valuation", help="Query smoke test")
    return parser


def main() -> None:
    """Load documents from CLI."""
    settings = get_cached_settings()
    configure_logging(settings.log_level, settings.logs_dir / "chroma_loader.log")
    for logger_name in ("httpx", "httpcore", "huggingface_hub"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    args = build_arg_parser().parse_args()
    documents = load_jsonl(args.input, args.limit)
    loader = ChromaDocumentLoader(collection_name=args.collection, model_name=args.model)
    summary = loader.upsert_documents(documents, args.batch_size)
    print(
        json.dumps(
            {
                "collection_name": summary.collection_name,
                "document_count": summary.document_count,
                "persisted_path": str(summary.persisted_path),
            },
            ensure_ascii=False,
        )
    )
    if args.smoke_test:
        rows = loader.similarity_search(args.query, n_results=3)
        for row in rows:
            preview = row["text"][:180].replace("\n", " ")
            print(
                json.dumps(
                    {
                        "doc_id": row["doc_id"],
                        "distance": row["distance"],
                        "metadata": row["metadata"],
                        "preview": preview,
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()

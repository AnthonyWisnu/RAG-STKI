"""Modul retrieval KG dan vector."""

try:
    from src.retrieval.agentic_router import AgenticRouter
    from src.retrieval.kg_retriever import KGRetriever
    from src.retrieval.vector_retriever import VectorRetriever
except ModuleNotFoundError:
    from backend.src.retrieval.agentic_router import AgenticRouter
    from backend.src.retrieval.kg_retriever import KGRetriever
    from backend.src.retrieval.vector_retriever import VectorRetriever

__all__ = ["AgenticRouter", "KGRetriever", "VectorRetriever"]

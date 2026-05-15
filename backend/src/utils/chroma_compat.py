"""Compatibility helpers for ChromaDB on Windows."""

from __future__ import annotations

import sys
import types


def disable_chromadb_default_onnx() -> None:
    """Prevent ChromaDB from initializing its default ONNX embedder.

    ScoutRAG always passes multilingual E5 embeddings explicitly when writing
    and querying ChromaDB. Chroma's default ONNX embedder is therefore unused,
    but ChromaDB 0.5 initializes it during import. On some Windows setups,
    onnxruntime fails to load its DLL and breaks the whole import.
    """
    if "onnxruntime" not in sys.modules:
        sys.modules["onnxruntime"] = types.ModuleType("onnxruntime")

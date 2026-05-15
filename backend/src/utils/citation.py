"""Citation helpers for KG and vector retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Citation:
    """Citation payload used by API responses."""

    id: str
    label: str
    source: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable citation."""
        data = asdict(self)
        if data["metadata"] is None:
            data.pop("metadata")
        return data


def kg_citation_from_row(row: dict[str, Any], index: int = 0) -> Citation:
    """Build KG citation from a Cypher row."""
    player = row.get("player") or row.get("name") or row.get("p.name") or "KG row"
    season = row.get("season") or row.get("se.id")
    league = row.get("league") or row.get("l.name")
    valuation_date = row.get("valuation_date")
    if valuation_date:
        return Citation(
            id=f"kg:{index}:{player}:{valuation_date}",
            label=f"{player} - valuation {valuation_date}",
            source=str(row.get("source") or "Neo4j Knowledge Graph"),
        )
    parts = [str(item) for item in (player, season, league) if item]
    return Citation(
        id=f"kg:{index}:{':'.join(parts) if parts else 'row'}",
        label=" - ".join(parts) if parts else f"Knowledge Graph row {index + 1}",
        source="Neo4j Knowledge Graph",
    )


def vector_citation_from_metadata(metadata: dict[str, Any], doc_id: str) -> Citation:
    """Build vector citation from Chroma metadata."""
    label_parts = [
        metadata.get("player_name"),
        metadata.get("doc_type"),
        metadata.get("season"),
    ]
    label = " - ".join(str(item) for item in label_parts if item)
    return Citation(
        id=f"vector:{doc_id}",
        label=label or str(doc_id),
        source=str(metadata.get("source") or "ChromaDB document"),
        metadata=metadata,
    )

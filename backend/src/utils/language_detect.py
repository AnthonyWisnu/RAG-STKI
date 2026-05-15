"""Lightweight language detection for Indonesian and English queries."""

from __future__ import annotations

ID_HINTS = {
    "siapa",
    "berapa",
    "pemain",
    "nilai",
    "pasar",
    "terbaik",
    "terbanyak",
    "gol",
    "skor",
    "pencetak",
    "musim",
    "liga",
    "klub",
    "bandingkan",
    "jelaskan",
    "profil",
    "ringkasan",
}


def detect_language(text: str) -> str:
    """Detect only `id` or `en`, with Indonesian keyword override."""
    lowered = text.lower()
    if any(f" {hint} " in f" {lowered} " for hint in ID_HINTS):
        return "id"
    try:
        from langdetect import detect

        detected = detect(text)
        return "id" if detected == "id" else "en"
    except Exception:
        return "en"

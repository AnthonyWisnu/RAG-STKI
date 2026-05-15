"""Loader dataset Transfermarkt dari Kaggle."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import (
        KAGGLE_TRANSFERMARKT_DATASET,
        REQUIRED_TRANSFERMARKT_FILES,
        get_cached_settings,
    )
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import (
        KAGGLE_TRANSFERMARKT_DATASET,
        REQUIRED_TRANSFERMARKT_FILES,
        get_cached_settings,
    )
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class KaggleDatasetStatus:
    """Status file dataset Transfermarkt di folder lokal."""

    dataset_slug: str
    target_dir: Path
    required_files: tuple[str, ...]
    existing_files: tuple[str, ...]
    missing_files: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        """Mengembalikan True jika semua file wajib tersedia."""
        return len(self.missing_files) == 0


class KaggleLoaderError(RuntimeError):
    """Error saat validasi atau download dataset Kaggle gagal."""


def validate_kaggle_credentials(username: str, key: str) -> None:
    """Memastikan credential Kaggle tersedia sebelum download.

    Args:
        username: Username Kaggle dari environment.
        key: API key Kaggle dari environment.

    Raises:
        KaggleLoaderError: Jika salah satu credential kosong.
    """
    missing_fields = []
    if not username:
        missing_fields.append("KAGGLE_USERNAME")
    if not key:
        missing_fields.append("KAGGLE_KEY")
    if missing_fields:
        joined_fields = ", ".join(missing_fields)
        raise KaggleLoaderError(f"Credential Kaggle belum lengkap: {joined_fields}")


def inspect_dataset_files(
    target_dir: Path,
    required_files: Iterable[str] = REQUIRED_TRANSFERMARKT_FILES,
    dataset_slug: str = KAGGLE_TRANSFERMARKT_DATASET,
) -> KaggleDatasetStatus:
    """Memeriksa file Transfermarkt yang tersedia secara lokal.

    Args:
        target_dir: Folder tujuan dataset lokal.
        required_files: Daftar file CSV wajib.
        dataset_slug: Slug dataset Kaggle.

    Returns:
        Status kelengkapan dataset.
    """
    required_tuple = tuple(required_files)
    existing_files = tuple(
        sorted(file.name for file in target_dir.glob("*.csv"))
        if target_dir.exists()
        else ()
    )
    existing_set = set(existing_files)
    missing_files = tuple(file for file in required_tuple if file not in existing_set)
    return KaggleDatasetStatus(
        dataset_slug=dataset_slug,
        target_dir=target_dir,
        required_files=required_tuple,
        existing_files=existing_files,
        missing_files=missing_files,
    )


def download_transfermarkt_dataset(
    target_dir: Path | None = None,
    dataset_slug: str = KAGGLE_TRANSFERMARKT_DATASET,
    force: bool = False,
) -> KaggleDatasetStatus:
    """Mengunduh dataset Transfermarkt dari Kaggle dan validasi file wajib.

    Args:
        target_dir: Folder tujuan. Default memakai `backend/data/raw`.
        dataset_slug: Slug dataset Kaggle.
        force: Jika True, download ulang walaupun file wajib sudah lengkap.

    Returns:
        Status dataset setelah proses download atau validasi.

    Raises:
        KaggleLoaderError: Jika credential kosong, Kaggle API gagal, atau file wajib
            masih belum lengkap setelah download.
    """
    settings = get_cached_settings()
    output_dir = target_dir or settings.raw_data_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_kaggle_credentials(settings.kaggle_username, settings.kaggle_key)
    status_before = inspect_dataset_files(output_dir, dataset_slug=dataset_slug)
    if status_before.is_complete and not force:
        LOGGER.info("Dataset Kaggle sudah lengkap di %s", output_dir)
        return status_before

    LOGGER.info("Mengunduh dataset Kaggle %s ke %s", dataset_slug, output_dir)
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise KaggleLoaderError("Package kaggle belum terpasang") from exc

    try:
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(
            dataset=dataset_slug,
            path=str(output_dir),
            unzip=True,
            quiet=False,
        )
    except Exception as exc:
        raise KaggleLoaderError(f"Gagal download dataset Kaggle: {exc}") from exc

    status_after = inspect_dataset_files(output_dir, dataset_slug=dataset_slug)
    if not status_after.is_complete:
        missing = ", ".join(status_after.missing_files)
        raise KaggleLoaderError(f"File dataset wajib belum lengkap: {missing}")

    LOGGER.info("Dataset Kaggle lengkap: %s", ", ".join(status_after.required_files))
    return status_after


def build_arg_parser() -> argparse.ArgumentParser:
    """Membuat parser CLI untuk loader Kaggle."""
    parser = argparse.ArgumentParser(description="Download dataset Transfermarkt Kaggle")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="Folder tujuan dataset. Default backend/data/raw.",
    )
    parser.add_argument(
        "--dataset",
        default=KAGGLE_TRANSFERMARKT_DATASET,
        help="Slug dataset Kaggle.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download ulang walaupun file wajib sudah lengkap.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Hanya cek file lokal, tanpa download.",
    )
    return parser


def main() -> None:
    """Menjalankan loader Kaggle dari command line."""
    settings = get_cached_settings()
    configure_logging(settings.log_level)
    parser = build_arg_parser()
    args = parser.parse_args()

    target_dir = args.target_dir or settings.raw_data_dir
    if args.check_only:
        status = inspect_dataset_files(target_dir, dataset_slug=args.dataset)
        LOGGER.info("Folder dataset: %s", status.target_dir)
        LOGGER.info("File tersedia: %s", ", ".join(status.existing_files) or "-")
        LOGGER.info("File hilang: %s", ", ".join(status.missing_files) or "-")
        return

    status = download_transfermarkt_dataset(
        target_dir=target_dir,
        dataset_slug=args.dataset,
        force=args.force,
    )
    LOGGER.info("Status dataset lengkap: %s", status.is_complete)


if __name__ == "__main__":
    main()

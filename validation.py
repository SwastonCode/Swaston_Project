"""
Проверка загруженных архивов перед отправкой модераторам (п.12 ТЗ).

Важно: результат проверки НЕ является гарантией безопасности.
Исходный код никогда не запускается и не собирается на сервере.
"""
from __future__ import annotations

import logging
import mimetypes
import os
import zipfile
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    scan_summary: str = ""


def validate_archive(file_path: str, declared_filename: str) -> ValidationResult:
    reasons: list[str] = []

    # 1. Расширение
    ext = os.path.splitext(declared_filename)[1].lower()
    if ext not in config.ALLOWED_ARCHIVE_EXTENSIONS:
        reasons.append(f"Недопустимое расширение файла: {ext}")
        return ValidationResult(ok=False, reasons=reasons)

    # 2. MIME-тип
    mime, _ = mimetypes.guess_type(declared_filename)
    if mime not in ("application/zip", "application/x-zip-compressed", None):
        reasons.append(f"Недопустимый MIME-тип: {mime}")

    # 3. Размер файла
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > config.MAX_ARCHIVE_SIZE_MB:
        reasons.append(f"Файл превышает лимит размера: {size_mb:.1f}MB > {config.MAX_ARCHIVE_SIZE_MB}MB")
        return ValidationResult(ok=False, reasons=reasons)

    # 4. Проверка ZIP-архива + защита от ZIP-бомб + directory traversal
    if not zipfile.is_zipfile(file_path):
        reasons.append("Файл повреждён или не является корректным ZIP-архивом")
        return ValidationResult(ok=False, reasons=reasons)

    try:
        with zipfile.ZipFile(file_path) as zf:
            total_uncompressed = 0
            for info in zf.infolist():
                # Directory traversal
                normalized = os.path.normpath(info.filename)
                if normalized.startswith("..") or os.path.isabs(normalized):
                    reasons.append(f"Подозрительный путь в архиве (directory traversal): {info.filename}")
                    continue

                total_uncompressed += info.file_size

                # ZIP-бомба: аномальный коэффициент сжатия на отдельном файле
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > config.MAX_ZIP_COMPRESSION_RATIO:
                        reasons.append(
                            f"Подозрение на ZIP-бомбу: {info.filename} (коэффициент сжатия {ratio:.0f}x)"
                        )

            total_mb = total_uncompressed / (1024 * 1024)
            if total_mb > config.MAX_ZIP_UNCOMPRESSED_MB:
                reasons.append(
                    f"Суммарный распакованный размер превышает лимит: {total_mb:.1f}MB > "
                    f"{config.MAX_ZIP_UNCOMPRESSED_MB}MB"
                )
    except zipfile.BadZipFile:
        reasons.append("Ошибка чтения ZIP-архива")
        return ValidationResult(ok=False, reasons=reasons)

    # 5. ClamAV (опционально)
    scan_summary = _run_clamav_scan(file_path)
    if scan_summary.startswith("INFECTED"):
        reasons.append(f"ClamAV: {scan_summary}")

    ok = len(reasons) == 0
    return ValidationResult(ok=ok, reasons=reasons, scan_summary=scan_summary)


def _run_clamav_scan(file_path: str) -> str:
    if not config.CLAMAV_HOST:
        logger.info("ClamAV не настроен (CLAMAV_HOST пуст) — сканирование пропущено")
        return "SKIPPED (ClamAV не настроен)"

    try:
        import pyclamd  # type: ignore

        cd = pyclamd.ClamdNetworkSocket(config.CLAMAV_HOST, config.CLAMAV_PORT)
        result = cd.scan_file(file_path)
        if result is None:
            return "CLEAN"
        return f"INFECTED ({result})"
    except ImportError:
        logger.warning("pyclamd не установлен — сканирование пропущено")
        return "SKIPPED (pyclamd не установлен)"
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка при сканировании ClamAV: %s", exc)
        return f"SCAN_ERROR ({exc})"

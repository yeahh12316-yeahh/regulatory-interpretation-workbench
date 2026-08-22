"""Optional OCR adapter for image-only regulatory PDFs.

The API keeps OCR optional so a text-based PDF remains lightweight. When the
host provides Poppler and Tesseract, this adapter renders only the pages that
have no extractable text and returns page-keyed OCR text for evidence mapping.
Tesseract's automatic page segmentation mode is used first so rotated scans
are handled without silently rotating source pages or changing their page
locators.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class OCRUnavailableError(RuntimeError):
    """Raised when the host cannot execute the configured OCR fallback."""


def extract_ocr_pages(
    path: str | Path,
    page_numbers: list[int],
    *,
    languages: str = "chi_sim+eng",
    timeout_seconds: int = 120,
) -> dict[int, str]:
    if not page_numbers:
        return {}

    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        missing = ", ".join(name for name, value in (("pdftoppm", pdftoppm), ("tesseract", tesseract)) if not value)
        raise OCRUnavailableError(f"OCR 兜底不可用，缺少命令：{missing}")

    try:
        languages_result = subprocess.run(
            [tesseract, "--list-langs"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OCRUnavailableError(f"无法检查 OCR 语言包：{exc}") from exc
    available_languages = set(languages_result.stdout.split())
    requested_languages = languages.split("+")
    missing_languages = [language for language in requested_languages if language not in available_languages]
    if missing_languages:
        raise OCRUnavailableError(f"OCR 缺少语言包：{', '.join(missing_languages)}")

    result: dict[int, str] = {}
    with tempfile.TemporaryDirectory(prefix="regulation-ocr-") as temp_dir:
        temp_root = Path(temp_dir)
        for page_number in sorted(set(page_numbers)):
            prefix = temp_root / f"page-{page_number}"
            try:
                subprocess.run(
                    [
                        pdftoppm,
                        "-f",
                        str(page_number),
                        "-l",
                        str(page_number),
                        "-png",
                        "-r",
                        "200",
                        str(path),
                        str(prefix),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                image_candidates = sorted(temp_root.glob(f"page-{page_number}-*.png"))
                if not image_candidates:
                    raise OCRUnavailableError(f"OCR 未生成第 {page_number} 页图像")
                text_result = subprocess.run(
                    [tesseract, str(image_candidates[0]), "stdout", "-l", languages, "--psm", "3"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except OCRUnavailableError:
                raise
            except (OSError, subprocess.SubprocessError) as exc:
                raise OCRUnavailableError(f"第 {page_number} 页 OCR 失败：{exc}") from exc
            result[page_number] = text_result.stdout.strip()
    return result

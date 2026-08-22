from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader

from backend.app.services.ocr_fallback import OCRUnavailableError, extract_ocr_pages


ARTICLE_PATTERN = re.compile(r"^(第[〇零一二三四五六七八九十百千万两0-9]+条)\s*(.*)$")
CHAPTER_PATTERN = re.compile(r"^(第[〇零一二三四五六七八九十百千万两0-9]+章)\s*(.*)$")
APPENDIX_MARKER_PATTERN = re.compile(r"(?:附\s*[:：]?\s*[123一二三]|附[件录]\s*[一二三123])")
DOCUMENT_NO_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z0-9·]{1,24}[〔(（]\d{4}[〕)）]\s*\d+\s*号)")
DATE_PATTERN = re.compile(r"(20\d{2})[-年](\d{1,2})[-月](\d{1,2})")
EFFECTIVE_PATTERN = re.compile(r"自(20\d{2})年(\d{1,2})月(\d{1,2})日起施行")
VERSION_PATTERN = re.compile(r"(20\d{2}年(?:修订版|版))")


@dataclass(frozen=True)
class ParsedArticle:
    article_no: str
    chapter_no: str | None
    article_order: int
    original_text: str
    source_page: int
    source_offset: dict[str, Any]


@dataclass(frozen=True)
class ParsedRegulation:
    title: str
    document_no: str | None
    issuer: list[str]
    publish_date: date | None
    effective_date: date | None
    version_label: str
    page_count: int
    articles: list[ParsedArticle]
    warnings: list[str]
    extraction_summary: dict[str, Any]


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\u00a0", " ").replace("\r", "")


def _date_from_match(match: re.Match[str] | None) -> date | None:
    if match is None:
        return None
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _is_page_chrome(line: str) -> bool:
    compact = re.sub(r"\s+", "", line)
    return any(
        (
            re.match(r"^20\d{2}/\d{1,2}/\d{1,2}.*第\d+/\d+页", compact),
            compact.startswith("http://") or compact.startswith("https://"),
            compact in {"(/cnafc)", "(/cnafc/front/index.action)", "首页", "用户登录"},
            compact.startswith("上一篇：") or compact.startswith("下一篇：") or compact.startswith("相关链接："),
            compact.startswith("地址:") or compact.startswith("总机:") or compact.startswith("邮编:") or compact.startswith("传真:"),
            "版权所有" in compact or "京ICP备" in compact,
        )
    )


def _clean_page_lines(page_text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(normalize_text(page_text).splitlines(), start=1):
        line = raw_line.strip()
        if not line or _is_page_chrome(line):
            continue
        lines.append((line_number, line))
    return lines


def _is_scan_placeholder(page_text: str) -> bool:
    """Treat image-only PDF markers as unreadable so OCR can run.

    Some scanners add a tiny text layer such as ``Scanned by CamScanner``.
    That layer is not regulatory content and must not suppress the OCR
    fallback or make a scan appear successfully extracted.
    """

    compact = re.sub(r"\s+", "", normalize_text(page_text)).lower()
    return compact in {"scannedbycamscanner", "scannedbycamscanner."} or (
        "scannedbycamscanner" in compact and len(compact) <= 80
    )


def parse_pdf(
    path: str | Path,
    *,
    enable_ocr: bool = True,
    ocr_provider: Callable[[str | Path, list[int]], dict[int, str]] | None = None,
) -> ParsedRegulation:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    scan_pages = [
        page_number
        for page_number, text in enumerate(pages, start=1)
        if not text.strip() or _is_scan_placeholder(text)
    ]
    page_methods = ["empty" if page_number in scan_pages else "pypdf" for page_number in range(1, len(pages) + 1)]
    empty_pages = scan_pages
    warnings: list[str] = []
    ocr_pages: list[int] = []
    ocr_error: str | None = None
    if empty_pages and enable_ocr:
        try:
            ocr_text = (ocr_provider or extract_ocr_pages)(path, empty_pages)
            for page_number, text in ocr_text.items():
                if page_number in empty_pages and text.strip():
                    pages[page_number - 1] = text
                    page_methods[page_number - 1] = "ocr"
                    ocr_pages.append(page_number)
            if ocr_pages:
                warnings.append("部分页面通过 OCR 提取；相关条款需人工核验文字准确性")
        except OCRUnavailableError as exc:
            ocr_error = str(exc)
            warnings.append(ocr_error)
    full_text = "\n".join(normalize_text(page) for page in pages)
    first_article_position = re.search(r"第[〇零一二三四五六七八九十百千万两0-9]+条", full_text)
    header_text = full_text[: first_article_position.start()] if first_article_position else full_text[:3000]
    title_match = re.search(r"《([^》]{2,200})》", header_text)
    if title_match:
        title = title_match.group(1).strip()
    else:
        header_lines = _clean_page_lines(header_text)
        title = next(
            (
                line
                for _, line in header_lines
                if not DOCUMENT_NO_PATTERN.fullmatch(line.replace(" ", ""))
                and not CHAPTER_PATTERN.match(line)
                and not DATE_PATTERN.search(line)
                and "修订版" not in line
                and "版）" not in line
                and "版)" not in line
            ),
            Path(path).stem,
        )
    document_no_match = DOCUMENT_NO_PATTERN.search(header_text)
    document_no = document_no_match.group(1).replace(" ", "") if document_no_match else None
    version_match = VERSION_PATTERN.search(title) or VERSION_PATTERN.search(full_text)
    version_label = version_match.group(1) if version_match else "未标注版本"
    publish_date = _date_from_match(re.search(r"(?:时间|发布日期)\s*[:：]?\s*" + DATE_PATTERN.pattern, full_text))
    effective_date = _date_from_match(EFFECTIVE_PATTERN.search(full_text))
    issuer = ["财政部"] if "财政部" in full_text[:2000] else []

    articles: list[ParsedArticle] = []
    current: dict[str, object] | None = None
    current_chapter: str | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        text = "\n".join(str(line) for line in current["lines"] if str(line).strip()).strip()
        if text:
            articles.append(
                ParsedArticle(
                    article_no=str(current["article_no"]),
                    chapter_no=current["chapter_no"] if isinstance(current["chapter_no"], str) else None,
                    article_order=len(articles) + 1,
                    original_text=text,
                    source_page=int(current["source_page"]),
                    source_offset={
                        "page": int(current["source_page"]),
                        "line_start": int(current["line_start"]),
                        "line_end": int(current["line_end"]),
                        "extraction_method": str(current["extraction_method"]),
                    },
                )
            )
        current = None

    for page_number, page_text in enumerate(pages, start=1):
        for line_number, line in _clean_page_lines(page_text):
            chapter_match = CHAPTER_PATTERN.match(line)
            if chapter_match:
                current_chapter = chapter_match.group(1)
                continue
            article_match = ARTICLE_PATTERN.match(re.sub(r"^[\s·•.,。；;:：\-—_]+", "", line))
            if article_match:
                flush()
                current = {
                    "article_no": article_match.group(1),
                    "chapter_no": current_chapter,
                    "source_page": page_number,
                    "extraction_method": page_methods[page_number - 1],
                    "line_start": line_number,
                    "line_end": line_number,
                    "lines": [article_match.group(2).strip()] if article_match.group(2).strip() else [],
                }
                continue
            if current is not None:
                current["lines"].append(line)  # type: ignore[union-attr]
                current["line_end"] = line_number
        if current is not None:
            current["last_page"] = page_number

    flush()
    if not pages:
        warnings.append("文件没有可读取页面")
    if not articles:
        warnings.append("未识别到以‘第×条’开头的条款，请人工确认版式或补充 OCR")
    if any(not page.strip() for page in pages):
        warnings.append("部分页面没有可提取文本，可能需要 OCR")
    if "附" in full_text and not APPENDIX_MARKER_PATTERN.search(full_text):
        warnings.append("正文提及附件，但当前文件中未可靠识别附件标题")

    return ParsedRegulation(
        title=title,
        document_no=document_no,
        issuer=issuer,
        publish_date=publish_date,
        effective_date=effective_date,
        version_label=version_label,
        page_count=len(pages),
        articles=articles,
        warnings=warnings,
        extraction_summary={
            "pypdf_pages": [page_number for page_number, method in enumerate(page_methods, start=1) if method == "pypdf"],
            "ocr_pages": sorted(ocr_pages),
            "unreadable_pages": [page_number for page_number, method in enumerate(page_methods, start=1) if method == "empty"],
            "page_diagnostics": [
                {
                    "page": page_number,
                    "method": method,
                    "char_count": len(normalize_text(pages[page_number - 1]).strip()),
                    "status": "ocr_review_required" if method == "ocr" else ("unreadable" if method == "empty" else "extracted"),
                }
                for page_number, method in enumerate(page_methods, start=1)
            ],
            "ocr_error": ocr_error,
        },
    )

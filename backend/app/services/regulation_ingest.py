from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pypdf import PdfReader


ARTICLE_PATTERN = re.compile(r"^(第[〇零一二三四五六七八九十百千万两0-9]+条)\s*(.*)$")
CHAPTER_PATTERN = re.compile(r"^(第[〇零一二三四五六七八九十百千万两0-9]+章)\s*(.*)$")
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
    source_offset: dict[str, int]


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


def parse_pdf(path: str | Path) -> ParsedRegulation:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    full_text = "\n".join(normalize_text(page) for page in pages)
    title_match = re.search(r"《([^》]{2,200})》", full_text)
    title = title_match.group(1).strip() if title_match else Path(path).stem
    first_article_position = re.search(r"第[〇零一二三四五六七八九十百千万两0-9]+条", full_text)
    header_text = full_text[: first_article_position.start()] if first_article_position else full_text[:3000]
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
            article_match = ARTICLE_PATTERN.match(line)
            if article_match:
                flush()
                current = {
                    "article_no": article_match.group(1),
                    "chapter_no": current_chapter,
                    "source_page": page_number,
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
    warnings: list[str] = []
    if not pages:
        warnings.append("文件没有可读取页面")
    if not articles:
        warnings.append("未识别到以‘第×条’开头的条款，请人工确认版式或补充 OCR")
    if any(not page.strip() for page in pages):
        warnings.append("部分页面没有可提取文本，可能需要 OCR")
    if "附" in full_text and not re.search(r"附[件录]\s*[一二三四五六七八九十0-9]+", full_text):
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
    )

"""Stable ordering for article-level interpretation results.

Database identifiers are implementation details and must not determine the
order shown to a reviewer.  Article.article_order is the source of truth.
"""

from __future__ import annotations

from typing import TypeVar


Record = TypeVar("Record")


def article_order_key(item: Record) -> tuple[bool, int, str, str]:
    article = getattr(item, "article", None)
    order = getattr(article, "article_order", None)
    article_no = str(getattr(article, "article_no", "") or "")
    record_id = str(getattr(item, "article_id", "") or getattr(item, "requirement_id", ""))
    return (order is None, order if order is not None else 10**9, article_no, record_id)


def order_article_records(records: list[Record]) -> list[Record]:
    return sorted(records, key=article_order_key)

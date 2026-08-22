from types import SimpleNamespace

from backend.app.services.result_ordering import order_article_records


def test_order_article_records_uses_article_order_not_generated_ids():
    records = [
        SimpleNamespace(article_id="VER_ART_010", article=SimpleNamespace(article_order=10, article_no="第十条")),
        SimpleNamespace(article_id="VER_ART_002", article=SimpleNamespace(article_order=2, article_no="第二条")),
        SimpleNamespace(article_id="VER_ART_001", article=SimpleNamespace(article_order=1, article_no="第一条")),
    ]

    ordered = order_article_records(records)

    assert [item.article.article_no for item in ordered] == ["第一条", "第二条", "第十条"]

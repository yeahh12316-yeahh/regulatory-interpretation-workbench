from types import SimpleNamespace

from backend.app.services.version_compare import compare_regulation_versions


def _version(version_id, label, document_id, sha256, articles, previous_version_id=None):
    source_document = SimpleNamespace(document_id=document_id, file_name=f"{label}.pdf", sha256=sha256, page_count=3)
    version = SimpleNamespace(
        version_id=version_id,
        regulation_id="REG_COMPARE",
        version_label=label,
        publish_date=None,
        effective_date=None,
        source_document_id=document_id,
        source_sha256=sha256,
        source_document=source_document,
        articles=articles,
        previous_version_id=previous_version_id,
    )
    for article in articles:
        article.version = version
    return version


def _article(article_id, article_no, text, page):
    return SimpleNamespace(
        article_id=article_id,
        article_no=article_no,
        article_order=page,
        original_text=text,
        source_page=page,
        source_offset={"start": page * 100, "end": page * 100 + len(text)},
    )


def test_s5_never_generates_diff_without_old_source():
    current = _version("VER_NEW", "2026年版", "DOC_NEW", "a" * 64, [_article("A1", "第一条", "新规正文", 1)])

    result = compare_regulation_versions(current, None, relation_confirmed=True)

    assert result["stage_status"] == "skipped"
    assert result["output"]["comparison_status"] == "SKIPPED_NO_PREVIOUS_SOURCE"
    assert result["output"]["changes"] == []
    assert "old_source_document" in result["output"]["required_inputs"]


def test_s5_blocks_until_version_relation_is_confirmed():
    old = _version("VER_OLD", "2025年版", "DOC_OLD", "b" * 64, [_article("A0", "第一条", "旧规正文", 1)])
    current = _version("VER_NEW", "2026年版", "DOC_NEW", "a" * 64, [_article("A1", "第一条", "新规正文", 1)], "VER_OLD")
    current.previous_version = old

    result = compare_regulation_versions(current, old, relation_confirmed=False)

    assert result["stage_status"] == "blocked"
    assert result["output"]["comparison_status"] == "WAITING_RELATION_CONFIRMATION"
    assert result["output"]["changes"] == []


def test_s5_compares_added_deleted_modified_and_numeric_changes_with_evidence():
    old_articles = [
        _article("OLD_1", "第一条", "金融企业应当在5个月内报送核销情况。", 2),
        _article("OLD_2", "第二条", "金融企业应当建立责任认定制度。", 3),
    ]
    new_articles = [
        _article("NEW_1", "第一条", "金融企业应当在6个月内报送核销情况。", 4),
        _article("NEW_3", "第三条", "金融企业不得伪造核销材料。", 5),
    ]
    old = _version("VER_OLD", "2025年版", "DOC_OLD", "b" * 64, old_articles)
    current = _version("VER_NEW", "2026年版", "DOC_NEW", "a" * 64, new_articles, "VER_OLD")
    current.previous_version = old

    result = compare_regulation_versions(current, old, relation_confirmed=True)
    output = result["output"]

    assert result["stage_status"] == "completed"
    assert output["comparison_status"] == "COMPLETED"
    assert output["summary"]["counts"] == {"ADDED": 1, "DELETED": 1, "MODIFIED": 1}
    assert output["unchanged_article_count"] == 0
    assert output["interpretation_status"] == "NOT_GENERATED_S4_BOUNDARY"

    by_type = {change["change_type"]: change for change in output["changes"]}
    modified = by_type["MODIFIED"]
    assert modified["article_no"] == "第一条"
    assert "NUMERIC" in modified["change_dimensions"]
    assert modified["old_evidence"]["source_document_id"] == "DOC_OLD"
    assert modified["old_evidence"]["source_hash"] == "b" * 64
    assert modified["old_evidence"]["page"] == 2
    assert modified["new_evidence"]["source_document_id"] == "DOC_NEW"
    assert modified["new_evidence"]["page"] == 4
    assert modified["text_diff"]
    assert by_type["ADDED"]["old_evidence"] is None
    assert by_type["DELETED"]["new_evidence"] is None

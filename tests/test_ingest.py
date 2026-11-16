from pathlib import Path

from ingest import CHUNK_SIZE, read_report, split_text

PRESS_RELEASE = Path("data/reports/HLXB_2026-09-22_press_release_atlas3.md")


def test_read_report_returns_metadata():
    metadata, body = read_report(PRESS_RELEASE)
    assert metadata["ticker"] == "HLXB"
    assert metadata["doc_type"] == "press_release"
    assert metadata["date"] == "2026-09-22"
    assert body  # the text is not empty


def test_read_report_removes_html_comments():
    _, body = read_report(PRESS_RELEASE)
    assert "<!--" not in body


def test_split_text_keeps_chunks_small_and_loses_nothing():
    paragraphs = [f"Paragraph {i}. " + "x" * 300 for i in range(10)]
    chunks = split_text("\n\n".join(paragraphs))
    assert len(chunks) > 1
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)
    for paragraph in paragraphs:
        assert any(paragraph in chunk for chunk in chunks)
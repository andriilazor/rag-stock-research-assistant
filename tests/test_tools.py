from tools import get_financial_metrics, get_price_history, search_reports


def test_unknown_ticker_returns_error_text_not_exception():
    for tool, args in [
        (search_reports, {"query": "risks", "ticker": "ABCD"}),
        (get_price_history, {"ticker": "ABCD", "days": 5}),
        (get_financial_metrics, {"ticker": "ABCD"}),
    ]:
        assert "not found" in tool.invoke(args)


def test_ticker_is_case_insensitive():
    assert "P/E ratio: 35.5" in get_financial_metrics.invoke({"ticker": "nwe"})


def test_missing_pe_ratio_is_not_available():
    assert "P/E ratio: not available" in get_financial_metrics.invoke({"ticker": "HLXB"})


def test_price_history_returns_requested_days():
    lines = get_price_history.invoke({"ticker": "VTL", "days": 3}).splitlines()
    assert len([line for line in lines if line.startswith("2026-")]) == 3


def test_price_history_finds_nordwind_drop():
    text = get_price_history.invoke({"ticker": "NWE", "days": 30})
    assert "Biggest daily drop in this period: 2026-10-08: close 15.71" in text
    assert "previous close 17.74, change -11.44%" in text


def test_tools_return_sources():
    call = {"type": "tool_call", "id": "1", "name": "get_financial_metrics", "args": {"ticker": "NWE"}}
    assert get_financial_metrics.invoke(call).artifact == ["metrics.json"]
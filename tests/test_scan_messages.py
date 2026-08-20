import main


def test_scan_summary_reports_no_games():
    result = main.summarize_scan_result([], source="football", no_games=True)
    assert result["status"] == "no_games"
    assert "No games" in result["message"]


def test_scan_summary_reports_error():
    result = main.summarize_scan_result([], source="football", error=RuntimeError("SSL error"))
    assert result["status"] == "error"
    assert "SSL error" in result["message"]

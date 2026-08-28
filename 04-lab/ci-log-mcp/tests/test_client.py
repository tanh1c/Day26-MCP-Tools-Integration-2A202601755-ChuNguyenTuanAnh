from __future__ import annotations

from types import SimpleNamespace

from ci_log_mcp.client import build_search_arguments, choose_search_tool, normalize_tool_result, parse_server_info


def test_choose_search_tool_prefers_v2_when_metadata_advertises_it() -> None:
    metadata = {"tools": {"search_ci_logs": {"version": "1.0.0"}, "search_ci_logs_v2": {"version": "2.0.0"}}}

    assert choose_search_tool(metadata) == "search_ci_logs_v2"


def test_choose_search_tool_falls_back_to_v1_for_old_or_malformed_metadata() -> None:
    assert choose_search_tool({"tools": {"search_ci_logs": {"version": "1.0.0"}}}) == "search_ci_logs"
    assert choose_search_tool({"tools": "not-a-map"}) == "search_ci_logs"
    assert choose_search_tool({}) == "search_ci_logs"


def test_parse_server_info_reads_text_resource_and_handles_bad_json() -> None:
    result = SimpleNamespace(contents=[SimpleNamespace(text='{"version":"2.0.0","tools":{}}')])
    bad = SimpleNamespace(contents=[SimpleNamespace(text="not json")])

    assert parse_server_info(result)["version"] == "2.0.0"
    assert parse_server_info(bad) == {}


def test_build_search_arguments_only_sends_severity_to_v2() -> None:
    modern = build_search_arguments("search_ci_logs_v2", "ci.log", "ERROR", 5, "error")
    legacy = build_search_arguments("search_ci_logs", "ci.log", "ERROR", 5, "error")

    assert modern == {"log_path": "ci.log", "keyword": "ERROR", "limit": 5, "severity": "error"}
    assert legacy == {"log_path": "ci.log", "keyword": "ERROR", "limit": 5}


def test_normalize_tool_result_prefers_structured_content_then_text() -> None:
    structured = SimpleNamespace(structured_content={"api_version": "2.0"}, content=[])
    legacy = SimpleNamespace(structured_content=None, content=[SimpleNamespace(text="legacy result")])

    assert normalize_tool_result(structured) == {"api_version": "2.0"}
    assert normalize_tool_result(legacy) == "legacy result"

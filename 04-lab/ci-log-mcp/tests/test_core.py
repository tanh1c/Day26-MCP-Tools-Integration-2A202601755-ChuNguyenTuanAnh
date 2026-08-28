from __future__ import annotations

from pathlib import Path

import pytest

from ci_log_mcp.core import analyze_junit, resolve_input_file, search_log_v1, search_log_v2


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_resolve_input_file_rejects_path_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = _write(tmp_path / "outside.log", "ERROR escaped\n")

    with pytest.raises(ValueError, match="outside CI_LOG_ROOT"):
        resolve_input_file(str(outside), root=root)


def test_search_log_v2_is_case_insensitive_and_keeps_line_numbers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(
        tmp_path / "build.log",
        "2026-08-28 INFO boot\n"
        "2026-08-28 ERROR first failure\n"
        "2026-08-28 warning transient\n"
        "2026-08-28 error second failure\n",
    )

    result = search_log_v2("build.log", "ERROR")

    assert result["api_version"] == "2.0"
    assert result["total_matches"] == 2
    assert result["returned_matches"] == 2
    assert result["matches"] == [
        {"line": 2, "severity": "ERROR", "text": "2026-08-28 ERROR first failure"},
        {"line": 4, "severity": "ERROR", "text": "2026-08-28 error second failure"},
    ]


def test_search_log_v2_filters_severity_and_applies_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(
        tmp_path / "build.log",
        "INFO retry request\nWARNING retry request\nERROR retry request\nERROR retry request again\n",
    )

    result = search_log_v2("build.log", "retry", limit=1, severity="error")

    assert result["total_matches"] == 2
    assert result["returned_matches"] == 1
    assert result["matches"] == [{"line": 3, "severity": "ERROR", "text": "ERROR retry request"}]


def test_search_log_rejects_invalid_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "build.log", "ERROR boom\n")

    with pytest.raises(ValueError, match="limit must be between 1 and 1000"):
        search_log_v2("build.log", "ERROR", limit=0)


def test_search_log_v1_keeps_legacy_string_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "build.log", "INFO ok\nERROR boom\n")

    result = search_log_v1("build.log", "error")

    assert isinstance(result, str)
    assert "1 match(es)" in result
    assert "L2 [ERROR] ERROR boom" in result


def test_search_log_v1_reports_no_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "build.log", "INFO ok\n")

    assert search_log_v1("build.log", "ERROR") == "No matches for 'ERROR' in build.log."


def test_analyze_junit_returns_counts_and_failure_details(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(
        tmp_path / "junit.xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="suite" tests="3" failures="1" errors="1" skipped="0" time="0.42">
  <testcase classname="tests.test_math" name="test_ok" time="0.01" />
  <testcase classname="tests.test_math" name="test_fail" time="0.02">
    <failure message="expected 2">assert 1 == 2</failure>
  </testcase>
  <testcase classname="tests.test_api" name="test_error" time="0.03">
    <error message="connection refused">traceback line</error>
  </testcase>
</testsuite>
""",
    )

    result = analyze_junit("junit.xml")

    assert result["tests"] == 3
    assert result["failures"] == 1
    assert result["errors"] == 1
    assert result["skipped"] == 0
    assert result["passed"] == 1
    assert result["problem_tests"] == [
        {
            "classname": "tests.test_math",
            "name": "test_fail",
            "kind": "failure",
            "message": "expected 2",
            "details": "assert 1 == 2",
        },
        {
            "classname": "tests.test_api",
            "name": "test_error",
            "kind": "error",
            "message": "connection refused",
            "details": "traceback line",
        },
    ]


def test_resolve_input_file_rejects_empty_missing_and_directory_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="path must not be empty"):
        resolve_input_file("   ")

    with pytest.raises(FileNotFoundError, match="does not exist"):
        resolve_input_file("missing.log")

    directory = tmp_path / "logs"
    directory.mkdir()
    with pytest.raises(ValueError, match="not a regular file"):
        resolve_input_file("logs")


def test_search_log_v2_rejects_unsupported_severity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "build.log", "ERROR boom\n")

    with pytest.raises(ValueError, match="unsupported severity"):
        search_log_v2("build.log", "ERROR", severity="notice")


def test_search_log_v2_marks_lines_without_known_severity_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "build.log", "build failed without severity token\n")

    result = search_log_v2("build.log", "failed")

    assert result["matches"] == [
        {"line": 1, "severity": "UNKNOWN", "text": "build failed without severity token"}
    ]


def test_analyze_junit_rejects_non_junit_xml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    _write(tmp_path / "report.xml", "<report />")

    with pytest.raises(ValueError, match="unsupported JUnit root element"):
        analyze_junit("report.xml")

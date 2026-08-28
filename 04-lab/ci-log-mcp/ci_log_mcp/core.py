from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_SEVERITY_RE = re.compile(r"\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE)
_SEVERITY_ALIASES = {"WARN": "WARNING", "FATAL": "CRITICAL"}


def _configured_root() -> Path:
    return Path(os.getenv("CI_LOG_ROOT", ".")).resolve()


def resolve_input_file(path: str, root: Path | None = None) -> Path:
    """Resolve an input path while preventing reads outside the configured root."""
    if not path.strip():
        raise ValueError("path must not be empty")

    allowed_root = (root or _configured_root()).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = allowed_root / candidate
    candidate = candidate.resolve()

    if not candidate.is_relative_to(allowed_root):
        raise ValueError(f"path is outside CI_LOG_ROOT: {path}")
    if not candidate.exists():
        raise FileNotFoundError(f"input file does not exist: {path}")
    if not candidate.is_file():
        raise ValueError(f"input path is not a regular file: {path}")
    return candidate


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")


def _normalize_severity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    normalized = _SEVERITY_ALIASES.get(normalized, normalized)
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if normalized not in allowed:
        raise ValueError(f"unsupported severity: {value}")
    return normalized


def _detect_severity(line: str) -> str:
    match = _SEVERITY_RE.search(line)
    if match is None:
        return "UNKNOWN"
    value = match.group(1).upper()
    return _SEVERITY_ALIASES.get(value, value)


def search_log_v2(
    log_path: str,
    keyword: str,
    limit: int = 20,
    severity: str | None = None,
) -> dict[str, object]:
    """Search a CI log and return structured, line-numbered matches."""
    _validate_limit(limit)
    if not keyword.strip():
        raise ValueError("keyword must not be empty")

    source = resolve_input_file(log_path)
    wanted_severity = _normalize_severity(severity)
    needle = keyword.casefold()
    matches: list[dict[str, object]] = []

    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            text = raw_line.rstrip("\r\n")
            if needle not in text.casefold():
                continue
            detected = _detect_severity(text)
            if wanted_severity is not None and detected != wanted_severity:
                continue
            matches.append({"line": line_number, "severity": detected, "text": text})

    returned = matches[:limit]
    return {
        "api_version": "2.0",
        "source": log_path,
        "keyword": keyword,
        "severity": wanted_severity,
        "total_matches": len(matches),
        "returned_matches": len(returned),
        "matches": returned,
    }


def search_log_v1(log_path: str, keyword: str, limit: int = 20) -> str:
    """Legacy v1 search contract retained for backward compatibility."""
    result = search_log_v2(log_path, keyword, limit=limit)
    matches = result["matches"]
    assert isinstance(matches, list)
    if not matches:
        return f"No matches for '{keyword}' in {log_path}."

    lines = [f"Found {result['total_matches']} match(es) in {log_path} (showing {result['returned_matches']}):"]
    for item in matches:
        assert isinstance(item, dict)
        lines.append(f"L{item['line']} [{item['severity']}] {item['text']}")
    return "\n".join(lines)


def _int_attr(element: ET.Element, name: str, default: int = 0) -> int:
    value = element.attrib.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _suite_totals(root: ET.Element, testcases: list[ET.Element]) -> tuple[int, int, int, int]:
    if root.tag == "testsuite":
        tests = _int_attr(root, "tests", len(testcases))
        failures = _int_attr(root, "failures", sum(case.find("failure") is not None for case in testcases))
        errors = _int_attr(root, "errors", sum(case.find("error") is not None for case in testcases))
        skipped = _int_attr(root, "skipped", sum(case.find("skipped") is not None for case in testcases))
        return tests, failures, errors, skipped

    suites = root.findall(".//testsuite")
    tests = sum(_int_attr(suite, "tests") for suite in suites) or len(testcases)
    failures = sum(_int_attr(suite, "failures") for suite in suites)
    errors = sum(_int_attr(suite, "errors") for suite in suites)
    skipped = sum(_int_attr(suite, "skipped") for suite in suites)
    return tests, failures, errors, skipped


def analyze_junit(report_path: str) -> dict[str, object]:
    """Summarize a JUnit XML file and extract failed/error test details."""
    source = resolve_input_file(report_path)
    root = ET.parse(source).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError(f"unsupported JUnit root element: {root.tag}")

    testcases = root.findall(".//testcase")
    tests, failures, errors, skipped = _suite_totals(root, testcases)
    problem_tests: list[dict[str, Any]] = []

    for case in testcases:
        problem = case.find("failure")
        kind = "failure"
        if problem is None:
            problem = case.find("error")
            kind = "error"
        if problem is None:
            continue
        problem_tests.append(
            {
                "classname": case.attrib.get("classname", ""),
                "name": case.attrib.get("name", ""),
                "kind": kind,
                "message": problem.attrib.get("message", ""),
                "details": (problem.text or "").strip(),
            }
        )

    return {
        "api_version": "1.0",
        "source": report_path,
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "passed": max(tests - failures - errors - skipped, 0),
        "problem_tests": problem_tests,
    }

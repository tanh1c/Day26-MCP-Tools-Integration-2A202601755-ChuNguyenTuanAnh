from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import Client

from ci_log_mcp.server import EnvTokenVerifier, mcp


@pytest.mark.asyncio
async def test_env_token_verifier_accepts_only_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_AUTH_TOKEN", "expected-token")
    verifier = EnvTokenVerifier()

    accepted = await verifier.verify_token("expected-token")
    rejected = await verifier.verify_token("wrong-token")

    assert accepted is not None
    assert accepted.client_id == "day26-ci-client"
    assert accepted.scopes == ["ci:read"]
    assert rejected is None


@pytest.mark.asyncio
async def test_env_token_verifier_rejects_when_server_token_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)

    assert await EnvTokenVerifier().verify_token("anything") is None


@pytest.mark.asyncio
async def test_mcp_discovers_all_submission_tools_and_metadata_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    (tmp_path / "ci.log").write_text("INFO start\nERROR failed test\n", encoding="utf-8")
    (tmp_path / "junit.xml").write_text(
        '<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase classname="x" name="y"><failure '
        'message="boom">assert false</failure></testcase></testsuite>',
        encoding="utf-8",
    )

    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        legacy = await client.call_tool("search_ci_logs", {"log_path": "ci.log", "keyword": "ERROR"})
        modern = await client.call_tool("search_ci_logs_v2", {"log_path": "ci.log", "keyword": "ERROR"})
        report = await client.call_tool("analyze_test_report", {"report_path": "junit.xml"})
        info = await client.read_resource("server://info")

    assert {tool.name for tool in tools.tools} >= {"search_ci_logs", "search_ci_logs_v2", "analyze_test_report"}
    assert {str(resource.uri) for resource in resources.resources} >= {"server://info"}
    assert legacy.content[0].text.startswith("Found 1 match(es)")
    assert modern.structured_content is not None
    assert modern.structured_content["api_version"] == "2.0"
    assert report.structured_content is not None
    assert report.structured_content["failures"] == 1
    metadata = json.loads(info.contents[0].text)
    assert metadata["version"] == "2.0.0"
    assert metadata["tools"]["search_ci_logs"]["deprecated"] is True
    assert metadata["tools"]["search_ci_logs"]["replacement"] == "search_ci_logs_v2"


@pytest.mark.asyncio
async def test_version_aware_client_reads_metadata_and_selects_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ci_log_mcp.client import run_connected

    monkeypatch.setenv("CI_LOG_ROOT", str(tmp_path))
    (tmp_path / "ci.log").write_text("INFO ok\nERROR selected by v2\n", encoding="utf-8")

    async with Client(mcp) as client:
        output = await run_connected(client, "ci.log", "ERROR", limit=10, severity="error")

    assert output["selected_tool"] == "search_ci_logs_v2"
    assert output["server_info"]["version"] == "2.0.0"
    assert output["result"]["api_version"] == "2.0"

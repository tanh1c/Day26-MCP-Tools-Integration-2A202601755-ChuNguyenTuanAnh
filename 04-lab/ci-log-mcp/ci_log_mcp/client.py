from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any


def choose_search_tool(metadata: dict[str, object]) -> str:
    """Prefer v2 only when server metadata explicitly advertises it."""
    tools = metadata.get("tools")
    if isinstance(tools, dict) and "search_ci_logs_v2" in tools:
        return "search_ci_logs_v2"
    return "search_ci_logs"


def parse_server_info(resource_result: object) -> dict[str, object]:
    """Parse JSON text from an MCP read_resource result; malformed metadata safely falls back to v1."""
    contents: object = getattr(resource_result, "contents", None)
    if not isinstance(contents, list) or not contents:
        return {}
    text: object = getattr(contents[0], "text", None)
    if not isinstance(text, str):
        return {}
    try:
        value: object = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


def build_search_arguments(
    tool_name: str,
    log_path: str,
    keyword: str,
    limit: int,
    severity: str | None,
) -> dict[str, object]:
    """Build arguments without sending v2-only fields to a legacy server."""
    arguments: dict[str, object] = {"log_path": log_path, "keyword": keyword, "limit": limit}
    if tool_name == "search_ci_logs_v2" and severity is not None:
        arguments["severity"] = severity
    return arguments


def normalize_tool_result(result: object) -> object:
    """Convert an MCP CallToolResult to a JSON-printable value."""
    structured: object = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    content: object = getattr(result, "content", None)
    if not isinstance(content, list):
        return content
    texts = [getattr(item, "text", None) for item in content]
    strings = [item for item in texts if isinstance(item, str)]
    if len(strings) == 1:
        return strings[0]
    return strings


async def run_connected(
    client: Any,
    log_path: str,
    keyword: str,
    limit: int = 20,
    severity: str | None = None,
) -> dict[str, object]:
    """Read server metadata first, select the compatible search tool, then execute it."""
    resource = await client.read_resource("server://info", cache_mode="refresh")
    metadata = parse_server_info(resource)
    tool_name = choose_search_tool(metadata)
    arguments = build_search_arguments(tool_name, log_path, keyword, limit, severity)
    result = await client.call_tool(tool_name, arguments)
    return {
        "selected_tool": tool_name,
        "server_info": metadata,
        "result": normalize_tool_result(result),
    }


async def run_remote(
    server_url: str,
    token: str,
    log_path: str,
    keyword: str,
    limit: int = 20,
    severity: str | None = None,
) -> dict[str, object]:
    """Connect over authenticated Streamable HTTP, read metadata, then call the compatible search tool."""
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    timeout = httpx2.Timeout(30.0, read=300.0)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client(server_url, http_client=http_client)
        async with Client(transport) as client:
            return await run_connected(client, log_path, keyword, limit=limit, severity=severity)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Version-aware client for the Day26 CI Log Analyst MCP server")
    parser.add_argument("--server-url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--token", default=None, help="Bearer token; defaults to MCP_AUTH_TOKEN")
    parser.add_argument("--log-path", default="samples/ci.log")
    parser.add_argument("--keyword", default="ERROR")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--severity", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> None:
    args = _parser().parse_args()
    token = args.token or os.getenv("MCP_AUTH_TOKEN")
    if not token:
        raise SystemExit("Bearer token required via --token or MCP_AUTH_TOKEN")

    output = asyncio.run(
        run_remote(
            server_url=args.server_url,
            token=token,
            log_path=args.log_path,
            keyword=args.keyword,
            limit=args.limit,
            severity=args.severity,
        )
    )
    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(f"Selected tool: {output['selected_tool']}")
    rendered = (
        json.dumps(output["result"], ensure_ascii=False, indent=2)
        if isinstance(output["result"], dict)
        else output["result"]
    )
    print(rendered)


if __name__ == "__main__":
    main()

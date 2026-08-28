from __future__ import annotations

import argparse
import hmac
import json
import os
from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ci_log_mcp import __version__
from ci_log_mcp.core import analyze_junit, search_log_v1, search_log_v2

DEFAULT_PORT = 8765
DEFAULT_RESOURCE_URL = f"http://127.0.0.1:{DEFAULT_PORT}/mcp"
DEFAULT_ISSUER_URL = "https://auth.example.com"

SERVER_INFO: dict[str, object] = {
    "name": "ci-log-analyst",
    "version": __version__,
    "capabilities": ["ci-log-search", "junit-analysis", "bearer-auth", "tool-versioning"],
    "tools": {
        "search_ci_logs": {
            "version": "1.0.0",
            "deprecated": True,
            "replacement": "search_ci_logs_v2",
            "output": "text/plain legacy string",
        },
        "search_ci_logs_v2": {
            "version": "2.0.0",
            "deprecated": False,
            "output": "structured JSON-compatible object",
        },
        "analyze_test_report": {
            "version": "1.0.0",
            "deprecated": False,
            "output": "structured JSON-compatible object",
        },
    },
}


class EnvTokenVerifier(TokenVerifier):
    """Verify the bearer token against MCP_AUTH_TOKEN without storing credentials in source."""

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = os.getenv("MCP_AUTH_TOKEN")
        if not expected or not hmac.compare_digest(token, expected):
            return None
        return AccessToken(token=token, client_id="day26-ci-client", scopes=["ci:read"])


def search_ci_logs(log_path: str, keyword: str, limit: int = 20) -> str:
    """[v1 legacy] Search a CI log and return a human-readable string."""
    return search_log_v1(log_path=log_path, keyword=keyword, limit=limit)


def search_ci_logs_v2(
    log_path: str,
    keyword: str,
    limit: int = 20,
    severity: str | None = None,
) -> dict[str, object]:
    """[v2] Search a CI log with structured line numbers, severities, counts, and optional severity filtering."""
    return search_log_v2(log_path=log_path, keyword=keyword, limit=limit, severity=severity)


def analyze_test_report(report_path: str) -> dict[str, object]:
    """Analyze a JUnit XML report and return totals plus failure/error details."""
    return analyze_junit(report_path)


def server_info() -> str:
    """Return server/tool version metadata used by version-aware clients."""
    return json.dumps(SERVER_INFO, ensure_ascii=False, sort_keys=True)


def create_server(resource_url: str = DEFAULT_RESOURCE_URL) -> MCPServer[Any]:
    """Create a fully registered MCP server for stdio, in-process tests, or Streamable HTTP."""
    issuer_url = os.getenv("MCP_ISSUER_URL", DEFAULT_ISSUER_URL)
    server = MCPServer(
        "ci-log-analyst",
        version=__version__,
        instructions=(
            "Analyze local CI logs and JUnit reports. "
            "Read server://info before choosing between legacy and v2 search tools."
        ),
        token_verifier=EnvTokenVerifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(issuer_url),
            resource_server_url=AnyHttpUrl(resource_url),
            required_scopes=["ci:read"],
        ),
    )
    server.tool()(search_ci_logs)
    server.tool()(search_ci_logs_v2)
    server.tool()(analyze_test_report)
    server.resource("server://info", mime_type="application/json")(server_info)
    return server


mcp = create_server()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Day26 CI Log Analyst MCP Server")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--resource-url",
        default=None,
        help="Public MCP resource URL used in auth metadata; defaults to http://127.0.0.1:<port>/mcp",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    if not os.getenv("MCP_AUTH_TOKEN"):
        raise SystemExit("MCP_AUTH_TOKEN must be set before starting authenticated HTTP transport")

    resource_url = args.resource_url or os.getenv("MCP_RESOURCE_URL") or f"http://127.0.0.1:{args.port}/mcp"
    http_server = create_server(resource_url=resource_url)
    http_server.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()

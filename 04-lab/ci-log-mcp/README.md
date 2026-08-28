# Day26 Hard Lab — CI Log Analyst MCP

This is the final Day26 submission implementation. It turns a real manual developer task — opening CI logs and JUnit reports to find failures — into MCP tools that an AI client can discover and call.

The implementation intentionally goes beyond the minimum lab requirements: authenticated Streamable HTTP, backward-compatible tool versioning, a `server://info` resource, a metadata-aware client, path-safety checks, unit/integration tests, strict lint/type checks, Docker, and GitHub Actions evidence.

## 1. Manual workflow replaced by MCP

Before this server, the workflow is typically:

1. Open a CI log file.
2. Search for `ERROR`, `FAILED`, or another keyword.
3. Count matching lines and inspect their severity/line numbers.
4. Open a JUnit XML report separately.
5. Find failed/error test cases and copy their messages.

The MCP server exposes these operations directly so Claude Code or another MCP client can decide when to call them.

## 2. Tools

| Tool | Version | Input | Output | Compatibility |
|---|---:|---|---|---|
| `search_ci_logs` | 1.0 | `log_path`, `keyword`, `limit=20` | Legacy human-readable string | Kept unchanged for old clients |
| `search_ci_logs_v2` | 2.0 | Same inputs plus optional `severity` | Structured object with counts, line numbers, severity and text | Preferred by new clients |
| `analyze_test_report` | 1.0 | `report_path` | Structured JUnit totals and failed/error test details | Current |

The tools read real files under `CI_LOG_ROOT`; they do not return fixed demo text. Relative paths are resolved inside that root and path traversal outside it is rejected.

## 3. Versioning and `server://info`

The server publishes:

```text
server://info
```

The resource contains the server version, capabilities, tool versions, deprecation state, and the v1 → v2 replacement mapping. The bundled client always reads this resource first. If `search_ci_logs_v2` is advertised it uses v2; otherwise it falls back to `search_ci_logs`.

This demonstrates backward compatibility: old clients can keep calling v1 while new clients get structured v2 output.

## 4. Install

From this directory:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install runtime + development dependencies:

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

The project pins the current MCP Python SDK major used by this submission:

```text
mcp[cli]==2.1.1
```

## 5. Run with stdio

No auth token is required for stdio because bearer authentication is an HTTP transport concern.

```bash
python -m ci_log_mcp.server --transport stdio
```

You can also inspect the server with MCP tooling supported by your installed SDK.

## 6. Register with Claude Code

Run Claude Code from `04-lab/ci-log-mcp/` after installing the package in the active environment.

A project-local `.mcp.json` is included for the stdio server:

```json
{
  "mcpServers": {
    "ci-log-analyst": {
      "command": "python",
      "args": ["-m", "ci_log_mcp.server", "--transport", "stdio"]
    }
  }
}
```

Equivalent Claude Code CLI registration (project scope):

```bash
claude mcp add --transport stdio --scope project ci-log-analyst -- \
  python -m ci_log_mcp.server --transport stdio
```

Then run `claude mcp list` or use `/mcp` inside Claude Code to confirm that the server and tools appear.

Natural-language checks for the lab:

```text
Find the ERROR lines in samples/ci.log and tell me which failures matter most.
```

```text
Read samples/junit.xml and summarize the failing tests.
```

Do not instruct Claude to call a specific tool by name during this check; the purpose is to verify that the agent discovers and selects MCP tools itself.

## 7. Authenticated Streamable HTTP

Generate a temporary token at runtime; do not put it in Git:

```bash
export MCP_AUTH_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CI_LOG_ROOT="$(pwd)"
python -m ci_log_mcp.server --transport http --host 127.0.0.1 --port 8765
```

The MCP endpoint is:

```text
http://127.0.0.1:8765/mcp
```

The protected-resource metadata endpoint is:

```text
http://127.0.0.1:8765/.well-known/oauth-protected-resource/mcp
```

For LAN/deployment use, bind to `0.0.0.0` and set the public MCP URL used in auth metadata:

```bash
export MCP_RESOURCE_URL="http://192.168.1.50:8765/mcp"
python -m ci_log_mcp.server --transport http --host 0.0.0.0 --port 8765
```

### Missing token → 401

```bash
curl -i -X POST http://127.0.0.1:8765/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

### Wrong token → 401

```bash
curl -i -X POST http://127.0.0.1:8765/mcp \
  -H 'Authorization: Bearer definitely-wrong' \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

### Valid token → MCP client reads metadata and calls a real tool

In another shell with the same `MCP_AUTH_TOKEN`:

```bash
python -m ci_log_mcp.client \
  --server-url http://127.0.0.1:8765/mcp \
  --log-path samples/ci.log \
  --keyword ERROR \
  --severity error \
  --json
```

Expected key evidence:

```json
{
  "selected_tool": "search_ci_logs_v2"
}
```

For a Claude Code HTTP configuration, use token expansion from the environment rather than a literal credential. Current Claude Code MCP configuration supports HTTP servers with an `Authorization` header sourced from an environment variable, for example conceptually:

```json
{
  "mcpServers": {
    "ci-log-http": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_AUTH_TOKEN}"
      }
    }
  }
}
```

Use HTTPS rather than plain HTTP when the server leaves a trusted local/LAN environment.

## 8. Test and quality checks

Run locally:

```bash
ruff check .
ruff format --check .
mypy ci_log_mcp
pytest -q --cov=ci_log_mcp --cov-report=term-missing --cov-fail-under=75
```

Core tests cover log parsing, line numbers, severity filters, limits, no-match behavior, JUnit parsing, and path traversal. MCP integration tests verify tool/resource discovery, v1 compatibility, v2 structured output, token verification, and metadata-first client selection.

## 9. Docker

Build:

```bash
docker build -t day26-ci-log-mcp .
```

Run with a runtime-generated token:

```bash
docker run --rm -p 8765:8765 \
  -e MCP_AUTH_TOKEN="$MCP_AUTH_TOKEN" \
  day26-ci-log-mcp
```

No credential is baked into the image or repository.

## 10. GitHub Actions policy

`.github/workflows/day26-ci.yml` intentionally minimizes unnecessary CI usage:

- Pull requests to `main` run CI only when Day26 submission/workflow files change.
- Ordinary pushes to a feature branch before a PR do **not** run CI.
- Once a PR exists, commits to that PR automatically retrigger CI.
- Push/merge to `main` runs the final verification once.
- Superseded runs for the same ref are cancelled.

The single CI job performs:

1. Ruff lint and format check.
2. MyPy strict type check.
3. Pytest + coverage + JUnit report.
4. Live Streamable HTTP server startup.
5. Missing-token and wrong-token HTTP 401 checks.
6. Valid-token version-aware MCP client call.
7. Docker build.
8. Upload of coverage/JUnit/client/server evidence artifacts.

## 11. Grading checklist

### Easy

- [x] MCP Server exists and starts.
- [x] At least 1–2 self-built tools; this submission has 3.
- [x] Tools solve a real developer workflow and read real files.
- [x] Tool inputs and outputs are documented.
- [x] Claude Code stdio configuration/instructions are included.
- [x] Natural-language verification prompts are included.

### Medium

- [x] Streamable HTTP transport.
- [x] `TokenVerifier` bearer authentication.
- [x] Valid token can call a real MCP tool.
- [x] Missing token is rejected with HTTP 401.
- [x] Wrong token is rejected with HTTP 401.
- [x] LAN/public resource URL can be configured without code changes.

### Hard

- [x] Real tool response format changes from v1 string to v2 structured data.
- [x] v1 remains available for old clients.
- [x] New fields/parameters are additive and optional.
- [x] `server://info` exposes server/tool versions and deprecation metadata.
- [x] New client reads metadata before selecting the tool.
- [x] New client prefers v2 and falls back to v1.

### Engineering extras

- [x] Unit + MCP integration tests.
- [x] Coverage threshold (75% minimum).
- [x] Ruff + MyPy strict checks.
- [x] Docker build.
- [x] Path traversal protection.
- [x] No committed credential.
- [x] GitHub Actions evidence artifacts.
- [x] CI path filters + concurrency cancellation to reduce wasted Actions runs.

## 12. Repository files

```text
04-lab/ci-log-mcp/
├── .mcp.json
├── Dockerfile
├── README.md
├── pyproject.toml
├── ci_log_mcp/
│   ├── __init__.py
│   ├── client.py
│   ├── core.py
│   └── server.py
├── samples/
│   ├── ci.log
│   └── junit.xml
└── tests/
    ├── test_client.py
    ├── test_core.py
    └── test_server.py
```

The original weather-agent material remains in the repository as a teaching/example implementation; `ci-log-mcp` is the submission built specifically against the Day26 hard-level requirements.

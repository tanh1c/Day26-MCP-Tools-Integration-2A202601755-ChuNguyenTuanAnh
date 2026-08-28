# Day26 MCP Tools Integration — Submission Report

## Student

- **Họ và tên:** Chu Nguyễn Tuấn Anh
- **MSSV:** 2A202601755
- **Track / Lab:** Track 3 — Day26 — MCP Tools Integration
- **Submission implementation:** [`04-lab/ci-log-mcp/`](04-lab/ci-log-mcp/README.md)

## Project summary

Bài nộp xây dựng **CI Log Analyst MCP Server** để thay thế workflow thủ công khi developer phải mở CI log và JUnit report để tìm lỗi. Server cung cấp tool đọc dữ liệu thật từ file, hỗ trợ Claude Code qua stdio và Streamable HTTP có bearer-token authentication.

### MCP tools

1. `search_ci_logs` — v1, giữ contract chuỗi để backward compatibility.
2. `search_ci_logs_v2` — v2, trả structured data gồm số dòng, severity, text và count.
3. `analyze_test_report` — phân tích JUnit XML, trả tổng số test và chi tiết failure/error.

### Hard-level requirements

- [x] Real MCP tools, không hard-code kết quả vô nghĩa.
- [x] stdio transport cho Claude Code.
- [x] Streamable HTTP transport.
- [x] `TokenVerifier` bearer authentication.
- [x] Missing token bị từ chối HTTP 401.
- [x] Invalid token bị từ chối HTTP 401.
- [x] Valid token gọi MCP tool thành công.
- [x] v1 vẫn hoạt động cho old client.
- [x] v2 thay đổi response format theo hướng structured data.
- [x] `server://info` chứa server/tool version, capability, deprecated/replacement metadata.
- [x] New client đọc `server://info` trước khi chọn tool.
- [x] Client ưu tiên v2 và có fallback v1.

## Engineering extras

- [x] Unit tests + MCP integration tests.
- [x] Ruff lint + Ruff format check.
- [x] MyPy strict.
- [x] Coverage gate 75%.
- [x] Docker build.
- [x] Path traversal protection.
- [x] Runtime-generated auth token; không commit credential thật.
- [x] GitHub Actions evidence artifact.
- [x] CI path filters để tránh chạy Actions không cần thiết.
- [x] Concurrency cancellation cho superseded runs.

## Final automated verification

**Verified implementation commit:** `7a76859238aeae61b6df28a33f34bb741bba35cd`

**GitHub Actions run #4:**

https://github.com/tanh1c/Day26-MCP-Tools-Integration-2A202601755-ChuNguyenTuanAnh/actions/runs/33166985957

Kết quả trên chính `main`:

| Check | Result |
|---|---|
| Install | PASS |
| Ruff lint | PASS |
| Ruff format | PASS |
| MyPy strict | PASS |
| Pytest | **20 tests, 0 failures/errors** |
| Coverage | **76.38%** — gate 75% |
| Authenticated Streamable HTTP startup | PASS |
| Missing token | **HTTP 401** |
| Invalid token | **HTTP 401** |
| Valid-token MCP client | PASS |
| Metadata-first tool selection | **`search_ci_logs_v2` selected** |
| Docker image build | PASS |
| Evidence artifact upload | PASS |

CI artifact name: `day26-mcp-ci-evidence`.

> Các commit sau verified implementation commit chỉ bổ sung documentation/evidence. Core implementation vẫn là phiên bản đã được final CI xác nhận.

## Claude Code verification

Project-local MCP configuration đã được cung cấp trong `04-lab/ci-log-mcp/.mcp.json` và hướng dẫn đầy đủ nằm trong `04-lab/ci-log-mcp/README.md`.

Sau khi cài dependency, có thể xác nhận bằng:

```bash
cd 04-lab/ci-log-mcp
python -m pip install -e ".[dev]"
claude mcp list
```

Natural-language prompts dùng để kiểm tra agent tự discover/call tool:

```text
Find the ERROR lines in samples/ci.log and tell me which failures matter most.
```

```text
Read samples/junit.xml and summarize the failing tests.
```

### Manual Claude Code evidence

Evidence directory: [`04-lab/ci-log-mcp/evidence/`](04-lab/ci-log-mcp/evidence/README.md)

Upload the captured screenshot with this exact path/name:

```text
04-lab/ci-log-mcp/evidence/claude-code-mcp-verification.png
```

Direct screenshot link after upload: [`claude-code-mcp-verification.png`](04-lab/ci-log-mcp/evidence/claude-code-mcp-verification.png)

The evidence README is already configured to render that image automatically. No further documentation edit is required after uploading the PNG.

The screenshot verifies the manual part that automated CI cannot replace: Claude Code receives a natural-language request, connects to `ci-log-analyst`, reads `server://info`, calls the MCP server, and returns real data from `samples/ci.log` / `samples/junit.xml`.

## Important files

- `04-lab/ci-log-mcp/README.md` — hướng dẫn chạy và grading checklist chi tiết.
- `04-lab/ci-log-mcp/ci_log_mcp/server.py` — MCP server, tools, resource và auth.
- `04-lab/ci-log-mcp/ci_log_mcp/client.py` — metadata-aware MCP client.
- `04-lab/ci-log-mcp/ci_log_mcp/core.py` — logic xử lý log/JUnit.
- `04-lab/ci-log-mcp/tests/` — automated tests.
- `.github/workflows/day26-ci.yml` — CI pipeline.
- `04-lab/ci-log-mcp/.mcp.json` — Claude Code stdio configuration.
- `04-lab/ci-log-mcp/evidence/README.md` — manual Claude Code evidence index.

## Submission status

**Code + automated verification: READY.**

**Manual Claude Code verification: captured; upload `claude-code-mcp-verification.png` to the prepared evidence directory to include the screenshot in the repository.**

After that single image upload, the repository contains the implementation, README, student information, submission report, automated CI evidence, Claude Code configuration/instructions, and manual Claude Code screenshot evidence required for submission.

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

> Các commit sau verified implementation commit chỉ bổ sung documentation ở root (`README.md`, `SUBMISSION.md`). Workflow được cấu hình chỉ chạy khi thay đổi `.github/workflows/day26-ci.yml`, `04-lab/ci-log-mcp/**` hoặc `.gitignore`, nên documentation-only updates này không làm thay đổi code đã được CI xác nhận và không tiêu tốn thêm CI run.

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

Phần Claude Code là manual client verification; CI đã tự động xác nhận MCP protocol, tools/resources, HTTP authentication, metadata-first selection và Docker build mà không cần lưu credential hoặc Claude account trong repository.

## Important files

- `04-lab/ci-log-mcp/README.md` — hướng dẫn chạy và grading checklist chi tiết.
- `04-lab/ci-log-mcp/ci_log_mcp/server.py` — MCP server, tools, resource và auth.
- `04-lab/ci-log-mcp/ci_log_mcp/client.py` — metadata-aware MCP client.
- `04-lab/ci-log-mcp/ci_log_mcp/core.py` — logic xử lý log/JUnit.
- `04-lab/ci-log-mcp/tests/` — automated tests.
- `.github/workflows/day26-ci.yml` — CI pipeline.
- `04-lab/ci-log-mcp/.mcp.json` — Claude Code stdio configuration.

## Submission status

**Code + automated verification: READY.**

Repository có đầy đủ implementation, README, student information, submission report, automated evidence và hướng dẫn Claude Code. Nếu giảng viên yêu cầu ảnh/video chứng minh thao tác trực tiếp trong Claude Code, cần thực hiện manual prompt ở trên và chụp lại kết quả; bước đó không thể được GitHub Actions thay thế bằng Claude account của sinh viên.

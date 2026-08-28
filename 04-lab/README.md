# Day26 Lab Submission

## Final submission — CI Log Analyst MCP

The graded Day26 implementation is in [`ci-log-mcp/`](./ci-log-mcp/README.md).

It is the submission built specifically for the hardest lab requirements:

- real file-backed MCP tools for CI logs and JUnit reports;
- stdio registration for Claude Code;
- authenticated Streamable HTTP with `TokenVerifier`;
- valid / missing / invalid bearer-token verification;
- backward-compatible v1 + structured v2 tool contracts;
- `server://info` version/capability metadata;
- a client that reads metadata before choosing v2 or falling back to v1;
- pytest, coverage, Ruff, MyPy, Docker, and GitHub Actions evidence.

See the submission README for installation, commands, Claude Code registration, authentication probes, versioning behavior, and the grading checklist.

## Previous example — Weather Agent

The existing `mcp-server/` and `mcp-client/` Weather Agent directories are retained as earlier learning/example material. They are not the final Day26 submission.

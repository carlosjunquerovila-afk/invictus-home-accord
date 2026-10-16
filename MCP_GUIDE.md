# Home Accord — optional MCP bridge, candidate 0.2.0

The original household simulation now has a real **Streamable HTTP MCP server**
targeting protocol **2025-11-25**. It wraps the existing scheduling, scoped
simulated consent, commit and undo engine. There is no Alexa integration, LLM
runtime, resident identity verification or physical appliance control.

The Amazon simulated-experience path remains the main candidature. The bridge
adds a runnable interface for a compatible MCP host; it does not by itself prove
novelty, contest eligibility or full specification conformance. A later external ChatGPT agent exercised this server through a local Python HTTP client; see `agent_demo/live_agent_trace.json`. This is not a native MCP-host connection or Alexa integration. The public demonstration is linked in `README.md`; this package does not certify final submission.

## Reproduce a complete interaction

Python 3.10+; standard library only. No packages, account, credentials, external
network access or paid resources are needed for the demonstration.

```sh
python3 mcp_demo.py --output mcp_demo_result.json
python3 -m unittest discover -s . -v
```

The demo starts a **separate server process**, negotiates the MCP version, lists
four tools, proposes a schedule, proves commit is refused before both simulated
approvals, records Alice/Bob approvals, commits, reads the agenda, and undoes it.
The JSON transcript records the real local exchanges without bearer tokens or
session identifiers. The household example is synthetic. The process and
temporary state are removed when the demo ends.

## Connect a compatible local MCP host

Set `HOME_ACCORD_MCP_TOKEN` to your own random URL-safe token of 32–256 characters
in the server process environment. Do not paste a real credential into source.

```sh
python3 mcp_server.py --port 8766 --state /absolute/private/path/mcp-state.json
```

Configure the host for Streamable HTTP at `http://127.0.0.1:8766/mcp` with an
`Authorization: Bearer <your-local-token>` header. By default the operator has
**not** enabled simulated approval or commit/undo. To exercise those demo
operations, explicitly add `--demo-consent` to the startup command. This flag is
an operator acknowledgement of a simulation, not authentication of Alice or Bob.

This is a local bearer capability, not an OAuth implementation. Use a private
state directory and a different file from the web simulation's `state.json`.
**Only one process may own a state file.** The original storage has no
multi-process transactions; do not run both interfaces against the same file.
The local user/filesystem remain trusted. Do not expose this server publicly.

## Tools and protocol behavior

| Tool | Behavior |
| --- | --- |
| `accord_state` | Reads simulated agenda, proposals and receipts. |
| `accord_propose` | Adds a bounded proposal without committing the agenda. |
| `accord_consent` | Grants or withdraws a demo role's consent for the exact proposal. |
| `accord_transition` | Commits with both approvals, or undoes the latest unchanged commit. |

`initialize` returns the supported protocol, tools capability and a random
`Mcp-Session-Id`. Subsequent POSTs include that session and
`MCP-Protocol-Version: 2025-11-25`, and accept both `application/json` and
`text/event-stream`. Send `notifications/initialized` before tools. Responses
use JSON; GET returns 405 because no unsolicited SSE stream is implemented.
DELETE ends a session. `ping` is supported. Only advertised capabilities exist:
there are no tasks, sampling, resources, prompts or logging subscriptions.

Tool arguments are validated against the published schemas. Tool execution
errors use `isError:true`; protocol errors use JSON-RPC error objects. Unknown
notifications receive HTTP 202 with no JSON-RPC reply and never execute tools.
Request IDs cannot repeat within a session. Limits are 64 KiB request bodies,
32 sessions, one-hour sessions, 4096 request IDs per session, 120 tool calls per
minute per session, and 64 durable proposals per demo workspace.

## Changes and review findings

New files: `mcp_server.py`, `test_mcp.py`, `mcp_demo.py`, `MCP_GUIDE.md`.
Existing files changed: `app.py`, `test_http.py`.

The legacy web interface now validates an explicit loopback Host and requires
an exact same-origin Origin on POST. The previous comparison reflected an
arbitrary Host, allowing a DNS-rebinding scenario. HTTP scripts using that
interface must now send its correct Origin. The browser UI continues to send it
automatically. Both interfaces remain local demonstrations with simulated roles.

Focused review also found and corrected malformed tool-name crashes, non-ASCII
authorization-header crashes, and uncorrelated JSON-RPC error IDs. The tests
exercise actual HTTP transport, consent/stale-plan gates, duplicate requests,
invalid JSON/types, Host/Origin/auth rejection, session lifecycle and persistence
rollback. Local tests and an additional AI review are not an external security
audit or a formal MCP conformance certification. The planner remains greedy,
does not model tariffs, quiet hours or task dependencies, and has no measured
energy savings or customer demand.

## Primary references checked 16 October 2026

- https://modelcontextprotocol.io/specification/2025-11-25/basic
- https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://amazonappdev2026.devpost.com/rules

Historical `AUDIT_REVIEW.json`, `TEST_RESULT.txt`, submission drafts and
eligibility notes describe the 6 October version; they are preserved as history.
Use this guide and the newly produced verification output for this candidate.

License: MIT, as in the original project. ChatGPT assisted implementation and
review; no claim of independent human audit, prize or monetization is made.

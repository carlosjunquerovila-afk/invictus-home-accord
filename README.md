# Home Accord 0.2.0

**Agree before the shared home acts.** A local simulated Alexa+ experience with a real Streamable HTTP MCP server: propose a household agenda, obtain scoped simulated consent, commit, inspect and undo.

**Historical evidence, 16 October 2026:** 23 internal tests passed. An external ChatGPT agent completed 13 JSON-RPC exchanges, including 11 tool calls, against a separate local MCP server process. The agent adapted its request after a refusal and completed a consent-gated, reversible agenda change. Recorded-command replay also passed.

**HTTP correction, 21 October 2026:** the local web simulator now rejects malformed request framing, bounds socket reads, returns structured storage-error responses and avoids claiming rollback when only the reply is lost after a committed write. The first correction passed a 25-test suite. Following a further response-delivery correction, all three targeted regression tests passed; the full 26-test suite was not rerun. `PACKAGE_MANIFEST.json` records these stages separately, the final targeted log and the current file hashes. This update creates no new agent trace, Alexa connection or device execution evidence.

The household and approvals are simulated. There is no Alexa connection, runtime LLM embedded in the app, native ChatGPT MCP connector, authenticated resident or physical appliance control. The competition path is the **Alexa+ simulated experience**; the implemented MCP surface is an additional runnable interface.

## Quick start

Python 3.10 or later and a modern browser are sufficient. No packages, API key, paid service or external network account are required.

```sh
python3 app.py
```

Open `http://127.0.0.1:8765`. The default state is stored in `state.json` next to the application. For a separate session:

```sh
python3 app.py --port 8765 --state ./home-accord-web-demo.json
```

In the browser, type `plan my evening`, then try `commit` before approval. The engine refuses it. Use `approve as Alice` and `approve as Bob`, then `commit`, `show agenda` and `undo`. These are explicitly simulated roles. Forms also expose requests and constraints. The command interface is a documented grammar, not unrestricted AI conversation.

Stop the process with Ctrl+C. Use synthetic data. Keep state files private and let only one process own a state file; the web and MCP interfaces must use different files.

## Reproduce the verification pipeline

Run from the repository root:

```sh
python3 -m unittest discover -s . -v
python3 mcp_demo.py --output mcp_demo_result.json
python3 agent_demo/verify_trace.py agent_demo/live_agent_trace.json
python3 agent_demo/agent_mcp_client.py --source . --commands agent_demo/replay_commands.jsonl --output agent_replay.json
python3 agent_demo/verify_trace.py agent_replay.json
```

The first command discovers the current internal tests, including the three HTTP regressions in `test_audit_http.py`. The historical 23-test result and the later correction results are distinct, as described above. `mcp_demo.py` starts a separate local server and exercises a complete simulated workflow. `verify_trace.py` audits stored evidence; it does not execute a model. The command replay starts a fresh local server with temporary state and explicit simulated-consent mode, performs real HTTP calls, then closes the session and process. It makes no new model inference.

To verify the current source distribution without running application tests, use `sha256sum -c SHA256SUMS.txt`. The preserved checksums under `historical/20261016/` describe the earlier distribution and must not be used as checksums of this corrected tree.

`agent_demo/live_agent_trace.json` records the original agent-directed run. Its SHA-256 is:

```text
a2063e6690828bf65bb9f8f2968aa4e07aa61f6d38d3961f3c39295f9f5e8c1b
```

## What the original agent actually did

| Step | Observation |
|---|---|
| Discover | Negotiated MCP 2025-11-25 and listed four tools. |
| Read | Observed the empty agenda and a 2,500 W ceiling. |
| Propose | Three 60-minute tasks requested within 60 minutes were refused by the planner. |
| Adapt | Widened the completion windows to 180 minutes without changing the power ceiling. |
| Attempt commit | Refused because both simulated residents had not approved. |
| Approve and commit | Recorded Alice/Bob demo approvals; committed three tasks at state version 1. |
| Inspect | Read a peak scheduled fixed demand of 2,000 W, below the unchanged ceiling. |
| Undo and inspect | Restored the original empty task list at version 2 and read it back. |

The ChatGPT agent selected each action after observing responses through tool execution and a Python transport client. The client contains no model. The application itself remains deterministic. The recorded-command demonstration replays those choices and must not be presented as another live AI decision sequence.

These observations describe one synthetic household. Relative planning minutes are not elapsed appliance execution. The dryer task is independent of the washing-machine task; no dependency is modeled.

## MCP interface

| Tool | Operation |
|---|---|
| `accord_state` | Read simulated agenda, proposals and receipts. |
| `accord_propose` | Add a proposal without changing the committed agenda. |
| `accord_consent` | Grant or withdraw a demo role's approval of one exact proposal. |
| `accord_transition` | Commit after both approvals, or undo the latest unchanged commit. |

The server targets MCP protocol 2025-11-25 over Streamable HTTP at `/mcp`. It supports initialization, tool discovery/calls, sessions, ping and session deletion. JSON responses are used; no unsolicited SSE stream, sampling, tasks, resources or prompt capabilities are advertised. This implementation has local tests, not a formal conformance certificate.

To connect a compatible local host, set `HOME_ACCORD_MCP_TOKEN` privately to a random URL-safe value of 32–256 characters, then run:

```sh
python3 mcp_server.py --port 8766 --state ./home-accord-mcp-demo.json
```

Configure the host for `http://127.0.0.1:8766/mcp` with the corresponding bearer header. Simulated consent and commit/undo are disabled unless the server is explicitly started with `--demo-consent`. That flag acknowledges a simulation; it does not authenticate Alice or Bob. Do not expose the server publicly or publish its token.

`MCP_GUIDE.md` contains transport details. The current guide and dated `agent_demo/` evidence describe the external agent run.

## Design and trust boundaries

- Scheduling is deterministic and greedy in 15-minute slots over a relative 180-minute horizon. A failed placement is not a general proof that no schedule exists.
- Fixed power ratings and exclusive resources are simplified inputs. There is no telemetry, tariff optimization, quiet-hours model, device interlock or measured energy saving.
- Consent is attached to the exact proposal and household version. A changed agenda or ceiling invalidates stale approvals. Simulated roles are not real identities.
- Undo applies only to the latest unchanged commit. It must not overwrite later work.
- Mutations are locked within one process; state uses atomic file replacement and in-memory rollback on failed writes. This does not provide multi-process transactions or fsync-backed power-loss guarantees.
- Local hash-linked receipts establish consistency, not authenticated identity, device execution or independent notarization. A privileged local owner can modify state and recompute hashes.

## Project history

The original project and repository were prepared on 6 October 2026 as a local web simulation. The 0.2.0 candidate added MCP transport, transport/security regression coverage and the external-agent trace of 16 October. Its historical 23-test total consisted of 12 inherited tests, ten MCP HTTP tests and one additional legacy HTTP security test. The 21 October correction adds three targeted HTTP regression tests while preserving that earlier evidence.

`TEST_RESULT.txt`, `AUDIT_REVIEW.json`, `PUBLICATION_TEST_RESULT.txt` and the dated `agent_demo/` and `demo_video/` records are retained historical evidence. Their earlier counts, hashes and absence-of-agent statements must not be reassigned to the corrected source. The original distribution manifest and checksums are preserved byte for byte under `historical/20261016/`. The root `PACKAGE_MANIFEST.json` and `SHA256SUMS.txt` describe the current corrected source distribution.

## Submission and attribution

Public author: **Carlosjv**. MIT licensed; the original license notice is retained. ChatGPT assisted research, design, implementation, testing and adversarial review. These reviews are internal, not an independent external audit.

Read `PROJECT_FEEDBACK.md` for tools actually used and `FRICTION_LOG.md` for observed onboarding feedback. No Amazon SDK, AWS runtime, deployed Alexa integration, customer adoption or revenue is claimed. The repository is the runnable prototype and its evidence; a final Devpost submission requires its own confirmation.

Official track requirements: https://amazonappdev2026.devpost.com/rules . The simulated-experience option is described under **Submission Requirements → Alexa+**. The MCP specification reference is https://modelcontextprotocol.io/specification/2025-11-25 .

## Included release assets

- `demo_video/Home_Accord_Demo_138s.mp4`: 138-second English-captioned execution viewer of a recorded real HTTP replay, with no audio track. It is not browser screen capture or fresh AI inference.
- `demo_video/Home_Accord_Demo_en.srt`: matching English subtitles.
- `demo_video/README.md`: recording method, limitations and optional renderer dependencies.
- `DEVPOST_STORY.md`, `PROJECT_FEEDBACK.md`, `FRICTION_LOG.md`: English submission materials.
- `PACKAGE_MANIFEST.json`: current source hashes, correction scope, dated verification stages and retained final targeted-test log.
- `SHA256SUMS.txt`: current distribution checksums, including the current package manifest and preserved historical files; excludes itself.
- `historical/20261016/`: original distribution manifest and checksums, preserved unchanged.

The source files and dated technical evidence remain in the package. Account credentials and runtime state are omitted. The two application/test files changed by the correction are identified separately from the documentation and manifest update.

## Public demonstration

https://www.youtube.com/watch?v=jUKCHt0pncw

Published 16 October 2026; 2:18, English captions embedded. This is a recorded HTTP execution viewer. This archive does not certify repository publication or final Devpost submission.

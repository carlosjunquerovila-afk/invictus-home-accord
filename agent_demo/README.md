# Home Accord: a live agent completed the MCP loop

On 16 October 2026, a ChatGPT agent interacted with the Home Accord MCP server through **real local HTTP**, choosing each next call after reading the preceding response. The household, resident roles, consent and appliances remain simulated. The application itself still contains no runtime LLM or Alexa integration.

The agent discovered the four tool schemas, read the 2,500 W limit, encountered a planner refusal, widened the requested time windows, encountered a consent refusal, recorded explicitly simulated role approvals, committed three tasks, read the resulting agenda, undid the change and read the restored agenda. The original application source was not changed.

## Observed result

| Evidence | Actual observation |
| --- | --- |
| MCP lifecycle | Protocol 2025-11-25, initialize, initialized notification, tool discovery, session deletion |
| Agent interaction | 13 JSON-RPC exchanges, including 11 tool calls, selected sequentially through the execution tool |
| Initial request | Three independent 60-minute tasks, all requested within 60 minutes; planner refused |
| Adaptation | Completion windows widened to 180 minutes without raising the 2,500 W ceiling |
| Proposed agenda | Washing machine 0–60 min, dishwasher 60–120 min, dryer 120–180 min |
| Power | Maximum scheduled fixed demand 2,000 W, below 2,500 W |
| Consent gate | Commit before Alice/Bob demo approvals returned an error |
| Application and reversal | Three tasks observed at version 1; empty original task list restored at version 2 |
| Existing regression suite | 23 tests passed in 6.257 seconds |

These are relative planning minutes, not timed physical execution. The dryer task is independent; no dependency on this washing-machine task is modeled. The power values are simplified application inputs, not telemetry. The greedy algorithm is not a global optimizer. Local receipts prove neither human identity nor real-world execution.

## Inspect the original evidence

`live_agent_trace.json` contains timestamps, requests, responses, the agent's decision notes made before each call, and SHA-256 hashes of the two server source files. It excludes the bearer capability, session identifier and temporary state location. The original process was stopped and its temporary state deleted at completion.

```sh
python3 verify_trace.py live_agent_trace.json
```

The verifier audits the recorded evidence; it does not rerun the model or certify the protocol. The original trace SHA-256 is:

`a2063e6690828bf65bb9f8f2968aa4e07aa61f6d38d3961f3c39295f9f5e8c1b`

## Reproduce the real transport

Use Python 3.10 or later. This folder is `agent_demo/` beneath the repository root. Run the following commands from `agent_demo/`; `--source ..` identifies the parent folder containing `app.py` and `mcp_server.py`. No packages, network account, API key or paid service is required.

```sh
python3 agent_mcp_client.py --source .. --commands replay_commands.jsonl --output your_replay.json
python3 verify_trace.py your_replay.json
```

This starts a separate loopback server process with a temporary state file and explicit `--demo-consent`, sends the recorded command sequence over HTTP, then closes the session and process. New proposal and receipt IDs are resolved from responses. **This reproduction is a deterministic command replay, not new agent inference.** `replay_validation.json` is the separately observed replay run included for convenience.

## Have an agent choose new actions

Run without `--commands`:

```sh
python3 agent_mcp_client.py --source .. --output new_interaction.json --operator-label "Describe the actual operator here"
```

Send one JSON line at a time, inspect its response, then select the next action. For example:

```json
{"method":"tools/list","params":{},"decision":"Discover the available operations before planning."}
{"method":"tools/call","params":{"name":"accord_state","arguments":{}},"decision":"Read the current ceiling and agenda."}
```

To stop cleanly:

```json
{"finish":true,"summary":"Describe only the outcomes actually observed."}
```

The client is only a transport and recorder. It does not contain, call, or impersonate an AI agent. In the original run, a ChatGPT agent supplied each command through tool execution after observing responses. This is not a native ChatGPT MCP connector integration, an Alexa connection, an independent external audit or a protocol conformance certification.

## Submission wording that the evidence supports

> Home Accord is a local simulation of a shared-household agent experience. A live ChatGPT agent exercised its MCP tools over HTTP, adapted a request after a planning failure, and completed a consent-gated, reversible agenda change. The scheduling engine and approval rules are deterministic. Resident approvals and appliance execution remain simulated; Alexa and physical devices are not connected.

The root `../TEST_RESULT.txt` and `../AUDIT_REVIEW.json` retain historical technical checks from the pre-agent iteration. The current root README and this dated evidence describe the external agent run. Do not claim that a runtime LLM was embedded into the app. The existing browser conversation still uses its documented command grammar.

## Recording package

`DEMO_SCRIPT_165_SECONDS.md` supplies a concise English voiceover and screen plan grounded in this actual run. Record the working interface/terminal and cite the observed results; the script is not a completed video. The completed execution-viewer video is included in `../demo_video/` and was published on 16 October 2026: https://www.youtube.com/watch?v=jUKCHt0pncw. This document does not certify final Devpost submission. A native Alexa integration, public deployment and validated customer willingness to pay are not established.

## Commercial hypothesis to test

The proposed buyer is a household-automation integrator who needs predictable approval and reversal before connecting assistants to real devices. The differentiating hypothesis is explicit shared-household consent attached to an exact proposed schedule. No customer interview, payment, quantified savings or demand has been verified. Before building billing, test whether integrators will pay for a pilot with authenticated residents and one safe device integration. Treat all pricing as an untested proposal.

The application retains its MIT license. This evidence package was created with ChatGPT assistance; it is not an independent human audit.

# Home Accord — observed friction log

**Public author:** Carlosjv · **Observed:** 16 October 2026  
**Scope:** documentation/onboarding feedback plus separately labelled internal engineering findings. No Amazon SDK or service integration was attempted, so none is reported as failing.

The official rules allow an optional friction-log judging bonus of up to 10%; no bonus is assumed or claimed here. Source: [Official Rules, Submission Requirements and Judges & Criteria](https://amazonappdev2026.devpost.com/rules).

## F01 — keep the simulated-experience exception next to the general runtime requirement

**Category:** hackathon documentation and route selection.  
**Severity:** low — additional clarification, not a build blocker after reading the full requirements.  
**Status:** understood and resolved for this project by reading the track-specific exception.

**Task attempted:** determine whether a local Alexa+ experience simulation needed an Amazon runtime SDK or an MCP interface to be eligible for its intended path.

**Steps taken:** read the overview's **Requirements → What to Submit** repository bullets, then the Alexa+ bullet below them, and cross-check **Official Rules → Submission Requirements → Alexa+**.

**Expected:** the general technology-use instruction would immediately identify the simulation option's different requirement.

**Observed:** the overview first describes actual runtime use for the named tracks, then gives the simulated-experience option in the Alexa+ detail. The rules explicitly exempt that option and still require its working source and demonstration. The exception exists; this is a discoverability observation, not a claim of contradictory rules.

**Impact observed in our preparation:** an initial interpretation treated MCP as mandatory. Reading the complete track-specific provision corrected it. No time-loss measurement or rejected submission is claimed. Home Accord's MCP bridge is a deliberate additional interface, not a purported mandatory repair for simulation eligibility.

**Workaround used:** consult both the overview's Alexa+ sub-bullet and the explicit exception in the rules; state the selected simulated path clearly in the README and submission.

**Actionable suggestion:** place a short “except the Alexa+ simulated-experience route below” cross-reference directly in the general runtime-use bullet, or present a two-row Alexa+ path table beside it. Show each path's runtime and demo requirements together.

**Evidence locations, checked 16 October 2026:**

- [Overview](https://amazonappdev2026.devpost.com/) → Requirements → What to Submit → repository runtime-use bullet, immediately followed by track-specific Alexa+ detail.
- [Official Rules](https://amazonappdev2026.devpost.com/rules) → Submission Requirements → repository runtime-use bullet and Alexa+ alternate-path paragraph.

No verbatim SDK error, screenshot of a failed Amazon call or vendor incident is attached because none occurred in this work.

## Internal engineering findings — not Amazon product friction

These entries are retained to explain our development controls. They should not be interpreted as faults in an Amazon tool or as additional entitlement to the friction bonus.

| Finding | Evidence and action | Attribution |
|---|---|---|
| Malformed tool names and non-ASCII authorization input could raise uncaught errors. | Internal MCP review; corrected input handling and regression coverage in `test_mcp.py`. | Our Python server implementation. |
| Some protocol error objects omitted the explicit null request ID for an unparseable request. | Internal review; corrected error shape and added coverage. | Our JSON-RPC handling. |
| The earlier web Host/Origin comparison reflected an arbitrary Host. | Review identified a DNS-rebinding scenario; replaced with explicit loopback Host and same-origin POST checks, covered in `test_http.py`. | Our legacy web implementation; not an observed external exploit. |
| The first 60-minute proposal was refused; commit without approvals was refused. | `agent_demo/live_agent_trace.json`: the agent widened the time windows, then supplied explicitly simulated role approvals. | Expected application behavior, not a vendor error or defect. |

## Requests for future integration work

For a future real-device implementation, the most important needs are authenticated resident consent, a documented confirmation boundary, state-aware reversal and safe device-specific operation. These are product requirements to investigate. They are not claims that an untested Amazon product lacks those capabilities.

# Home Accord

**Tagline:** A shared-home agent that plans within limits, asks everyone affected, and can reverse its last agenda change.

**Public author:** Carlosjv  
**Primary track:** Alexa+ — simulated experience  
**Built with:** Python, JavaScript, HTML, CSS, JSON-RPC, Model Context Protocol, ChatGPT

## Inspiration

A household assistant can affect more than the person who speaks first. If one resident requests the washing machine and another wants the dishwasher and dryer, producing a confident schedule is only part of the problem. The system also needs to respect shared limits, show the proposed change, obtain the relevant agreement and handle a change of mind.

Home Accord explores that interaction: **propose, agree, commit, inspect, undo**. Its focus is an agent's relationship with shared household state and permission to change it.

## What it does

Home Accord is a working local simulation with a web interface and a Streamable HTTP MCP server. It schedules independent appliance requests within a fixed power ceiling and time windows. A proposal does not change the agenda. The exact current proposal needs both simulated residents' approval before a commit. Changed state invalidates stale approvals, and undo can reverse the latest unchanged commit without overwriting later work.

The demonstration uses synthetic household data. Resident labels are selectable roles, not authenticated people. The application does not connect to Alexa or operate appliances.

## A real agent interaction, with a clear boundary

On 16 October, an external ChatGPT agent discovered the MCP tools and selected each next call after observing the previous response. The server refused the first requested schedule. The agent widened the completion windows from 60 to 180 minutes while retaining the 2,500 W ceiling.

The server then refused a commit without both approvals. After explicitly simulated Alice/Bob approvals, it committed three tasks, returned a locally recorded receipt, and allowed the agent to read the agenda. The highest scheduled fixed demand was 2,000 W. Undo restored the original empty task list, which the agent read back to check.

The trace contains 13 JSON-RPC exchanges, including 11 tool calls and two expected refusals. A separate recorded-command replay reproduces the flow over real local HTTP. Replay is not fresh model inference. The model runs outside the application through a small transport client; no runtime LLM or native ChatGPT MCP connector is embedded in the app.

## How it is built

Python's standard library implements the scheduling engine, local persistence, HTTP endpoints and MCP transport targeting protocol 2025-11-25. Four tools expose state, proposals, simulated consent and commit/undo. The browser uses the same deterministic engine through a bounded command interface and form controls.

The engineering emphasis is explicit state transitions: scoped consent, version checks, refused premature commits, rollback after failed persistence, and guarded reversal. The model chooses actions; the engine decides which transitions are allowed.

## Challenges and learning

Building the MCP transport required careful handling of initialization, sessions, invalid inputs and errors. Internal review found defects in our implementation, including malformed-input crashes and an overly permissive legacy Host/Origin comparison; these were corrected and covered by tests. These are our engineering findings, not reported defects in an Amazon SDK.

The interaction also reinforced a product lesson: an agent must be able to observe a refusal, adapt a request, and ask for agreement without silently relaxing the household's limit.

## What we are proud of

The current 0.2.0 candidate has 23 passing internal regression tests. The external-agent trace and replay add inspectable execution evidence. Reviewers can run the application and reproduce the recorded MCP interaction without paid services, API credentials or device purchases.

## Potential impact and what comes next

The intended audience is household-automation integrators exploring assistants that affect multiple residents. The proposed value is a reusable interaction pattern for agreement and reversible actions. There are no measured savings, customer interviews, paid pilots or revenue claims yet.

The next product work would be authenticated residents, one controlled device integration, device-specific safety constraints and a user study of whether the approval flow is understandable. The current planner is greedy, uses relative time and fixed power inputs, and does not model task dependencies, tariffs or physical execution.

## Project history and attribution

The project began on 6 October 2026 as a local web simulation. During the same submission window it gained a working MCP server, transport/security tests, a real external-agent interaction and reproducible trace evidence. Earlier documentation and test results are retained as dated history. The current version and reproduction instructions are in the repository README.

The project is MIT licensed. Carlosjv is the public author; ChatGPT assisted research, design, implementation, testing and review. Product feedback and a narrowly scoped friction log accompany the submission. No AWS Builder or separate Open Source mini-challenge achievement is claimed by this description.

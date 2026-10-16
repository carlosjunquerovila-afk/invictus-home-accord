# Home Accord — product and developer-tool feedback

**Author:** Carlosjv · **Version:** 0.2.0 · **Observed through:** 16 October 2026

This feedback concerns tools actually used. Home Accord follows the Alexa+ simulated-experience path and implements an additional local MCP server. No Alexa SDK, Amazon device API, AWS runtime, Ring SDK, Bee device/software or Fire TV runtime was executed. Accordingly, this report makes no claims about their setup time, reliability, performance or defects. It is not an AWS Builder mini-challenge claim.

## Model Context Protocol specification and our Streamable HTTP implementation

**Used for:** a four-tool interface around state, proposal, simulated consent and commit/undo. The Python implementation targets protocol 2025-11-25. A separate local HTTP client performed initialization, discovery and tool calls; the external agent chose actions after reading responses.

**What worked:** explicit schemas and structured results made the action boundary inspectable. A refused commit could remain a tool error while the session continued. The original trace and recorded-command replay show the complete interaction without embedding a model in the application.

**Onboarding and limitations:** implementing transport ourselves meant handling session lifecycle, protocol headers, error correlation and invalid input. Internal review found mistakes in our own server, which we fixed and tested. This is not evidence that the MCP specification or an Amazon SDK was defective. No native Alexa/ChatGPT MCP host interoperability or formal conformance certification was performed.

**Improvement request — important:** a compact, executable end-to-end reference fixture covering successful tool calls, refused actions, session closure and malformed requests would make it easier to compare a minimal server against expected behavior. This is a request based on our integration work, not a claim that no such resource exists anywhere.

**Would we use it again?** Yes, for a bounded agent/action boundary whose schemas and state transitions can be tested independently. Production work would require further interoperability and security validation.

## ChatGPT and the execution environment

**Used for:** research, design, implementation, internal adversarial review and the original agent-directed run. An external ChatGPT agent supplied commands sequentially through tool execution to our local HTTP client. This was not a native MCP connector and did not add a runtime model to the app.

**What worked:** after a planning refusal, the agent widened completion windows while preserving the 2,500 W ceiling. It inspected the results of commit and undo rather than treating the action request as sufficient evidence. The trace retains decision notes made before the calls, timestamps and responses.

**Limitations:** a replay of that trace does not test new model decisions. One synthetic successful interaction does not establish general agent reliability. AI-generated code and documentation required review; version-specific claims became stale as the project advanced.

**Improvement request — important:** exportable, sanitized tool traces that clearly separate a live model decision from deterministic replay would improve reviewability. Our recorder implements that distinction locally.

**Would we use it again?** Yes, with independently inspectable execution evidence, tests and explicit limits on what the agent may change.

## Python standard library and unittest

**Used for:** deterministic scheduling, local HTTP/MCP transport, JSON persistence, locking, subprocess-based demonstration and regression tests. The documented setup uses Python 3.10+ without third-party packages.

**What worked:** reviewers can run the local prototype and replay with a small dependency surface. Twenty-three tests cover consent, stale state, conflicts, reversal, malformed input, transport restrictions and persistence rollback.

**Limitations:** this lightweight server and state store are a local demonstration, not a deployment platform. One process must own a state file. Atomic replacement is not a claim of durable multi-process transactions or guaranteed survival of sudden power loss.

**Would we use it again?** Yes for a reproducible prototype. A production deployment would need a separately justified runtime, authenticated users and stronger persistence design.

## Browser technologies and GitHub

**Used for:** a dependency-free HTML/CSS/JavaScript interface and source distribution. The original public repository was prepared on 6 October; the current release keeps the original history and license while adding current reproduction evidence.

**What worked:** the web interface makes proposal, approval, commit and undo inspectable. The repository carries runnable source, test files and dated evidence rather than only a presentation.

**Limitations:** the browser conversation uses a listed command grammar. It is not speech recognition or unrestricted natural-language understanding. HTTP tests are not a user study or a complete accessibility audit. Repository publication is a distribution step, not proof of product quality.

**Would we use them again?** Yes, for transparent source review and a small local demonstrator.

## Hackathon onboarding documentation

The overview and official rules were used to choose the simulated-experience route. The exception is documented, but placing it directly beside the general runtime-use requirement would reduce the chance of an initial misread. `FRICTION_LOG.md` records the observed reading path, limited impact and suggested wording location. This feedback does not allege an SDK error or an unresolved contradiction in the rules.

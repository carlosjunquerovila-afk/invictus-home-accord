# Home Accord — English recording script

Target: 165 seconds, with roughly 240 spoken words and room for operation pauses. This is a recording plan, not an already recorded video. Use real output or clearly labeled playback of `live_agent_trace.json`. Never show capability tokens.

| Time | Show | Say |
| --- | --- | --- |
| 0–18 s | Product title, “local household simulation” badge, empty agenda | “A shared home has competing requests and one shared power limit. Home Accord lets an agent propose an agenda, but changing it requires both residents’ approval of that exact proposal.” |
| 18–35 s | Real MCP initialization and discovered tools; read state: 2,500 W | “This is a local simulation, with no Alexa or appliances connected. A live ChatGPT agent drove these MCP tools over HTTP. The application enforces the rules with deterministic code.” |
| 35–58 s | Tight-window request and actual refusal, then widened windows | “The agent first requests three independent, hour-long tasks within one hour. The planner cannot place them. After reading that response, the agent widens the windows to three hours without increasing the power limit.” |
| 58–78 s | Schedule: washer 0–60, dishwasher 60–120, dryer 120–180 | “The new proposal separates the tasks. Its highest scheduled demand is two thousand watts, below the two-thousand-five-hundred-watt ceiling. These values are simplified inputs, not device measurements, and this dryer task is independent.” |
| 78–105 s | Commit refusal; Alice and Bob simulated approvals | “An immediate commit is refused. Both residents must approve this exact proposal. We now explicitly simulate Alice and Bob’s approvals. These selectable roles are not authenticated people.” |
| 105–130 s | Successful commit, receipt, fresh state showing three tasks | “Only then does the agenda change. The agent reads state again and sees all three tasks at version one. The receipt records local consistency; it does not mean the appliances ran.” |
| 130–149 s | Undo response and fresh state: empty agenda, version 2 | “Now the agent undoes the latest change. A separate read confirms the original empty agenda has returned. Reversal is part of the workflow, not a promise in the pitch.” |
| 149–165 s | Trace verifier PASS; closing title and limits | “The evidence includes the actual requests, responses and decision notes. Twenty-three regression tests pass. Our next step is authenticated household consent and a carefully bounded device integration.” |

Recording requirements: show current source and output; distinguish live interaction from replay; maintain the simulation label; keep the final video under the applicable contest limit; add English captions. No award, savings, paying customer, physical execution or final submission is claimed.

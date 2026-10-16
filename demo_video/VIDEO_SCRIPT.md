# Home Accord — 138-second video script

Final video mode: animated execution viewer of a newly executed local HTTP replay.
The previous live-agent interaction supplied the command sequence. This replay performs no new AI inference.
Captions are English and burned into the image. The video has no audio track.

## 000–006 seconds: A shared home. An agreed agenda.
Home Accord: three household requests, one shared power limit. Local simulation; no appliances are connected.

## 006–012 seconds: Connect to the running MCP server
This is a paced replay of a live agent’s decisions, executed again over real local HTTP. No new AI inference occurs in this replay.

## 012–018 seconds: Discover the four available tools
The client discovers the server’s actual tools before proposing, approving, applying or undoing anything.

## 018–026 seconds: Read the current household state
The server reports an empty agenda, version zero, and a 2,500-watt ceiling. All times are relative planning minutes.

## 026–036 seconds: A tight request meets a real refusal
Three independent hour-long tasks cannot be placed in the requested one-hour window by this greedy planner.

## 036–042 seconds: Check that refusal changed nothing
A separate state read confirms the rejected request created neither tasks nor a saved proposal.

## 042–056 seconds: Adapt the request, preserve the limit
The recorded agent decision widens the windows to three hours. The server proposes sequential tasks below the unchanged 2,500-watt ceiling.

## 056–066 seconds: Missing simulated consent blocks commit
A premature commit is refused. Both demo roles must approve this exact proposal before the agenda can change.

## 066–074 seconds: Record the first simulated approval
Alice is a selectable demo role, not an authenticated person. This explicit simulation records only the first required approval.

## 074–082 seconds: Record the second simulated approval
Bob’s simulated approval is attached to the same proposal. Both required role approvals are now present.

## 082–094 seconds: Apply the exact approved proposal
The server returns a commit receipt at version one. We still read the agenda separately to verify the resulting state.

## 094–106 seconds: Verify the agenda after the commit
Three tasks are now observed in the agenda. Peak scheduled power is 2,000 watts; no physical device operation or energy savings are claimed.

## 106–116 seconds: Reverse the latest change
Undo returns a reversal receipt at version two. Receipts record local consistency, not human identity or appliance execution.

## 116–128 seconds: Read again: the original agenda returns
The final read shows an empty task list again. Reversal restored the original agenda while retaining the change history.

## 128–138 seconds: Propose. Agree. Apply. Undo.
13 recorded exchanges. 11 tool calls. Two refusals. A verified reversal. Full source, trace and run instructions accompany this demonstration.

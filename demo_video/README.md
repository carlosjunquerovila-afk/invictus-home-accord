# Home Accord — final demonstration video

`Home_Accord_Demo_138s.mp4` is an English-captioned, 2 minute 18 second demonstration. It is H.264 MP4, 1280×720, 12 fps, with fast-start metadata. Captions are burned into the image and also provided as `Home_Accord_Demo_en.srt`. There is no audio track, voice imitation, music or third-party logo.

## What was actually recorded

On 16 October 2026 at 11:06 UTC, the interactive MCP client started the existing Home Accord server as a separate loopback process and executed the earlier live agent's command sequence again. Every displayed response comes from that new real HTTP execution, recorded in `recorded_execution.json` and `recorded_terminal.jsonl`. A temporary state file and a fresh local bearer token were used; neither the token nor the session identifier is included in the evidence. The process and temporary state were removed after completion.

The MP4 is a paced, animated **execution viewer** built from these recorded exchanges. Requests and responses are revealed in order; the displayed household state, proposal, approvals and agenda derive from the corresponding responses. This is not a browser or desktop screen recording, not a mock response demonstration, and not a new AI inference run. A permanent “RECORDED MCP REPLAY” badge and a simulation label make that distinction visible. Display pacing was added for readability; request timestamps remain visible and represent actual execution times.

The original live interaction was performed separately by a ChatGPT agent choosing each next request after observing the previous response. Its transcript is `../agent_demo/live_agent_trace.json`. The application itself contains no runtime LLM, Alexa connection, authenticated residents or physical device control.

## Functionality shown

1. MCP 2025-11-25 initialization and discovery of four tools.
2. Read the empty agenda and fixed 2,500 W ceiling.
3. Observe rejection of three 60-minute tasks requested in a 60-minute window.
4. Confirm the rejected request left the agenda and saved plans unchanged.
5. Replay the agent's adaptation to 180-minute completion windows.
6. Observe commit refusal without both simulated role approvals.
7. Record explicitly simulated Alice and Bob approvals.
8. Commit, then read three actual agenda entries with peak scheduled power of 2,000 W.
9. Undo, then read the restored empty agenda at version 2.

All tasks and household data are synthetic. Power is a fixed input rather than measured demand. Task scheduling is greedy, uses relative minutes and does not model washer/dryer dependencies. Local receipts do not establish real-world execution or human identity.

## Verification and reproduction

`execution_verification.json` contains the observed PASS result, trace hash, 13 exchanges, 11 tool calls, two expected refusals and successful reversal. `MANIFEST.json` contains file hashes, video metadata and source provenance. Sample frames were visually inspected for readable captions, request/response layout, the committed schedule and the restored empty agenda. The application source was not changed to produce the video.

Run these commands from the `demo_video/` directory. To repeat the server execution with Python 3.10+:

```sh
python3 ../agent_demo/agent_mcp_client.py --source .. --commands ../agent_demo/replay_commands.jsonl --output new_recorded_execution.json
python3 ../agent_demo/verify_trace.py new_recorded_execution.json
```

To render the supplied recording again, use Python with Pillow installed, `ffmpeg` on PATH and the DejaVu fonts at `/usr/share/fonts/truetype/dejavu/` (the included renderer uses that Linux font path). Run from `demo_video/`:

```sh
python3 render_demo.py
```

The renderer resolves its input/output files relative to its own directory, so it uses the included `recorded_execution.json`. It overwrites the MP4, SRT and script, and also writes QA PNGs; render in a copy if preserving the release hashes. Reproduction on a different font, Pillow or ffmpeg version may change video bytes. The already rendered MP4 can be watched without these rendering dependencies.

Rendering does not contact a model, service or browser. The render source is included so judges can distinguish presentation from the recorded underlying functionality.

## Official video requirements checked

Source: [Amazon Developer Hackathon official rules](https://amazonappdev2026.devpost.com/rules), checked 16 October 2026, sections 4 and Language Requirements. The rules request a video shorter than three minutes, functioning project footage, public visibility on YouTube or Vimeo, and English materials or English translation. They also explicitly allow a simulated Alexa+ experience using an AI or agentic tool. The provided MP4 demonstrates executed local software through its execution viewer; it is not footage of connected Amazon hardware. Acceptance remains the organizer's decision.

The MP4 was published on 16 October 2026: https://www.youtube.com/watch?v=jUKCHt0pncw. This package does not certify final Devpost submission. The recording manifest retains its original recording-time publication statement; the current public URL is recorded in its packaging update and the root package manifest.

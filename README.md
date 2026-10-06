# Invictus Home Accord

A **local Alexa+ experience simulation**: a bounded multi-turn conversation turns competing household appliance requests into an agreed, reversible agenda. No Amazon integration, external API, runtime language model, speech recognition, or physical appliance control is implemented.

## Run

Requires Python 3.10+ and a modern browser; no packages, keys, cloud account, or network services required.

```sh
python3 app.py
```

Open http://127.0.0.1:8765. Data is stored in `state.json` next to the application. For an isolated session:

```sh
python3 app.py --port 8765 --state /tmp/home-accord-demo.json
```

## Walk through the agent simulation

1. Type `plan my evening`. The agent proposes a washing machine, dishwasher, and dryer schedule.
2. Type `commit` immediately. The backend refuses missing consent.
3. Type `approve as Alice`, then `approve as Bob`. Each approval applies to this exact proposal and household version.
4. Type `commit`. The local agenda changes and a receipt records simulated approvals and before/after hashes.
5. Type `undo`. The previous agenda returns, with a reversal receipt.
6. Try a new proposal, then `power 3000`. The changed household version invalidates earlier proposals and approvals.

Other commands: `withdraw as Alice`, `withdraw as Bob`, `show agenda`. Form controls provide the same real backend operations and custom windows/durations.

## What works

- Single-process persistent state, atomically replaced JSON file, lock around mutations, and in-memory rollback on failed persistence.
- Deterministic greedy planning in 15-minute slots across a relative 180-minute horizon.
- Fixed appliance power ratings and exclusive resource constraints, alongside a shared power ceiling.
- No agenda commit until both simulated residents approve the exact current proposal.
- Version checks prevent approval replay against an agenda or power limit that changed.
- Reversal only of the latest unchanged commit; later work is never overwritten by undo.
- Hash-linked local receipts, input validation, request-size limit, loopback binding, and cross-origin browser mutation refusal.

## Honest boundaries

This is an agent **workflow simulation**, not a deployed Alexa integration and not unrestricted AI conversation. The browser accepts a listed command grammar. Resident labels are selectable demo roles, **not authenticated identities**. Running this on a public server would require real authentication, authorization, CSRF protection, and stronger storage controls. Do not use private household data.

The planner is greedy, not globally optimal. A failed placement means this algorithm did not find a schedule, not a proof that none exists. It does not model dryer-after-washer dependencies, quiet hours, tariffs, device telemetry, safety interlocks, electricity-market data, or verified savings. Every task is independent. Power is a simplified fixed input rather than measured demand. Time is relative to the demo session, with no wall-clock execution.

Receipts establish local consistency only. Anyone able to modify the persisted state can recompute hashes; receipts are not signed or externally anchored, and they do not prove identity, physical execution, or a tamper-proof log. Atomic replacement and rollback do not provide fsync-backed power-loss guarantees or multi-process transaction support.

## Verify

```sh
python3 -m unittest discover -s . -v
```

Tests exercise missing/withdrawn consent, stale proposals, conflicting resources and power constraints, reversal, persistence/reload, duplicate commits, invalid requests, and disk-failure rollback. See `TEST_RESULT.txt` for the observed run. These tests are local correctness evidence; no external judge score or award is established.

## Competition draft

Prepared as a new project on 6 October 2026. `SUBMISSION_DRAFT.md` and `DEMO_SCRIPT.md` are preparation documents. No Amazon registration or submission is asserted. Public GitHub repository, working demo video, final product feedback, participant review, and acceptance of the contest terms remain outstanding.

Official rules: https://amazonappdev2026.devpost.com/rules

AI assistance: ChatGPT assisted research, architecture, implementation, and tests. The application itself uses deterministic scheduling and command parsing; it calls no generative model.

## License

MIT. Copyright 2026 Carlosjv.

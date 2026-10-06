# English working-demo script — target 2:35

Preparation: start with an empty state file; show the actual local application. Record working interactions, not a slide-only presentation. No footage or branding implying Amazon endorsement.

**0:00–0:20 — The problem**

“Household assistants act in shared spaces. A request from one person can conflict with another person’s needs. Home Accord shows an Alexa+ experience simulation that proposes first, waits for agreement, and keeps a way back.”

Show the simulation notice. “This is a deterministic local workflow, not a connected Alexa integration.”

**0:20–0:50 — Plan**

Type `plan my evening`. Show all three task requests and the proposed slots.

“The washing machine, dishwasher, and dryer compete for a 2,500-watt ceiling. The planner finds earliest feasible placements in a three-hour demo horizon. It does not claim global optimality.”

**0:50–1:20 — Refuse, then agree**

Type `commit`; show the refusal. Type `approve as Alice`, then `approve as Bob`.

“No schedule change can happen before both demo residents approve this exact proposal. These are selectable simulation roles, not authenticated real people.”

Type `commit`. Show agenda and receipt.

**1:20–1:45 — Reverse safely**

Type `undo`; show the restored empty agenda and reversal receipt.

“Undo restores the previous agenda only while the latest commit remains unchanged. These hashes check local record consistency; they do not prove real appliance execution.”

**1:45–2:15 — Reject stale consent**

Type `plan my evening`, `approve as Alice`, `approve as Bob`, `power 3000`, `commit`.

“Changing the power ceiling changes the household version. Old consent cannot silently authorize a changed plan.”

**2:15–2:35 — Close with boundaries**

“The source is small, reproducible, and tested against consent, resource, persistence, and reversal failures. A real integration would need authenticated residents and actual device constraints. The prototype demonstrates the agreement workflow, without pretending to have controlled a device.”

# Submission preparation — not submitted

**Project:** Invictus Home Accord  
**Primary track proposed:** Alexa+ — simulated experience  
**Participant public identity:** Carlosjv  
**Build started:** 6 October 2026  
**Status:** tested prototype with public source; no registration, submission, or prize confirmed

## Elevator pitch

A household assistant should help people agree before it acts. Home Accord demonstrates a conversational, stateful workflow that negotiates competing appliance requests within shared constraints, waits for scoped resident consent, and leaves a reversible receipt.

## What it does

In the web simulation, Alice and Bob request chores that compete for the household power ceiling. The deterministic planner proposes feasible time slots. Residents review and approve the exact proposal. The application refuses early execution, withdrawn consent, and stale approvals; after commitment, an unchanged latest agenda can be reversed without overwriting later work.

## How it is built

Python standard-library backend, atomically persisted JSON, locked mutations, and a dependency-free English web interface. A bounded command grammar drives the same backend operations as the form. This is explicitly a simulated Alexa+ experience with a deterministic workflow engine, not an Amazon integration or a runtime LLM. It does not control appliances or use external APIs.

## Why it matters

Domestic agents share resources and affect more than one person. The demonstration makes consent, conflicting requests, stale plans, and reversibility visible rather than treating a confident conversational response as permission. A future integration would require verified identities, actual device capabilities, and household-specific operating constraints. No user research, energy savings, customer traction, or live deployment is claimed.

## Validation

Local invariant and interface checks are recorded in TEST_RESULT.txt. They demonstrate behavior within the stated simplified model, not competitive ranking or production security.

## Tools and feedback

ChatGPT supported research, implementation, and adversarial review. Python standard-library HTTP and JSON storage keep the prototype reproducible without account setup. Their limitation is that this implementation is single-process and intended only for loopback use. No Alexa developer onboarding or SDK use occurred. The author therefore cannot honestly provide SDK-performance or actual Amazon-integration feedback.

## Still required before submission

- Complete registration after the mandatory Amazon developer-experience category is resolved. Registration terms were authorized on 6 October 2026.
- Final submission review and any final submission-specific agreement.
- Public English demonstration video under three minutes.
- Final truthful product/tool feedback and a draft-to-final eligibility review.
- Decide whether a separate, meaningful open-source contribution will be prepared for the additional mini challenge; this prototype alone does not establish that requirement.

Public source: https://github.com/carlosjunquerovila-afk/invictus-home-accord (MIT, setup instructions and tests published).

Official source: https://amazonappdev2026.devpost.com/rules

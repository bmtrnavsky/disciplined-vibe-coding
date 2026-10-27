---
name: verify
description: Use before done-claims, milestone completion, releases. Fresh evidence — terminal, user-attested, integrity, plus metric-band handling for nondeterministic work. Compact report, full table in plan, milestone retain. (Lineage: godmode/completion-gate, superpowers/verification-before-completion)
phase: Verify
---

# Verify — evidence or it didn't happen

## Prime directive
Nothing is done until fresh evidence, read in full, proves it.

## Steps (in order)
1. **Re-run, fresh.** Plan checks now; earlier output describes earlier code.
2. **Classify evidence honestly:**
   - *Terminal:* commands re-run this session.
   - *User-attested:* User-run checks; labeled, never simulated.
   - *Integrity:* data tasks — counts, checksums, sampled diffs, dry-run vs live. Zero-exit with wrong numbers FAILED.
   - *Metric:* model/eval tasks — compare against the plan's metric band. Nondeterministic runs: re-run with fixed seed where possible; report the observed values AND the band, honestly — "0.819 vs target 0.82" is a NEAR MISS to escalate, not a pass to fudge.
3. **Read all output.** Truncated → file → review. Skipped suites fail.
4. **Report compact, store complete.** "14 of 14 (10 terminal, 2 user, 1 integrity, 1 metric-in-band.)" Failures full. Table to plan file; one-liner rung has no plan file, so the chat summary IS the stored report.
5. **Milestone close:** mark complete; retain summary (shipped/decided/established) to Hindsight.
6. **MONEY-tier:** recommend one strong-model review pass over diffs+evidence before claiming done.
7. Plain language only. Releases gate here.

## Done when
- All checks green and classified; counted-format summary reported; failures shown in full; milestone retained iff applicable; strong-review recommendation issued on MONEY tier.

## Cognitive traps
- "Close enough is green" — a metric misses its band or it meets it; near-misses go to the user, not to fudge.
- "The command didn't error" — silent wrongness defines data work.
- "Memory accumulates by itself" — pages need retained summaries.

## Guardrails
- No done-claim without green summary mapped to the plan.
- No destructive done-claim without integrity evidence.
- Never tag/release with unverified work.

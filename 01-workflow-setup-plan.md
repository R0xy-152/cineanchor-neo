# Execution Plan — derived from approved requirements

> Author: Andy · Status: DRAFT for 启鸣 confirmation
> Basis: `01-workflow-setup-requirements.md` (approved 2026-06-26). Sequences the now-executable items into ordered, owned steps with gates.
> Legend — Owner: **启鸣** (human) / **Andy** (chat) / **CC** (Claude Code, local).
> Note: Phase 0 (Security & guardrails — token hardening, main protection) is dropped per 启鸣's decision (2026-06-27). R2 / R3 are shelved.

---

## Phase 1 — Establish the workflow (process, no product code)

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 1.1 | Adopt `00-workflow-rules.md` (this branch) as the binding ruleset | 启鸣 | 启鸣 approves the rules file |
| 1.2 | Append two-agent role split (R1) into `.claude/CLAUDE.md` | CC | 启鸣 reviews diff |
| 1.3 | Confirm handoff protocol (R4): Andy → `Andy` branch → 启鸣 review | Andy/启鸣 | This very loop proves it works |

---

## Phase 2 — Knowledge docs (lightweight, under `docs/`)

Build in this order — boundary first (highest value), then map, then decisions.

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 2.1 | `docs/scope.md` (R8): consolidate do/don't from AGENTS.md + CLAUDE.md | CC drafts, Andy reviews | 启鸣 approves; no out-of-scope items leak |
| 2.2 | `docs/codemap.md` (R9): one-page module map + call flow | CC drafts, Andy reviews | Map matches actual tree; shallow, regenerate-on-change |
| 2.3 | `docs/adr/` (R10): reconcile with existing local ADR set | CC | Continues from `ADR-004`; new ADRs merged, not forked |

Local ADR structure is known (`docs/adr/ADR-004-no-full-frame-ai-video-regeneration.md`), so 2.3 is no longer blocked — continue numbering from the existing set.

---

## Phase 3 — Execution loop becomes live

Once Phases 1–2 are done, the standing loop for every requirement is:

```
启鸣 states need
  → Andy clarifies + writes requirements/acceptance to `Andy` branch
  → 启鸣 reviews/approves on `Andy` branch
  → CC reads approved doc, runs PLAN MODE, writes plan
  → 启鸣 reviews plan  →  Andy reviews plan   (R5 double-review gate)
  → both pass → CC executes on a spike/* or feature/* branch
  → if output is video: CC renders locally, outputs test video PATH (R6)
  → 启鸣 accepts video → CC opens PR → 启鸣 merges
```

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 3.1 | Add lightweight pre-push smoke check (R7) | CC | Hook runs frame-count / black-frame / MP4-plays check |
| 3.2 | Run first real requirement end-to-end through the loop | all | One video accepted + merged via PR |

---

## Deferred (unchanged from requirements)

- R2 main protection / R3 token hardening — shelved per 启鸣 (2026-06-27).
- 历史口径 — no history yet; defer.
- Separate LLM Wiki — covered by CLAUDE.md + ADR.
- Path-allowlist CI (②) / CODEOWNERS (③) — dropped by choice.

---

## Critical path

`1.1 (rules approved)` → `2.1 scope` → loop goes live.
ADR (2.3) and codemap (2.2) can proceed in parallel.

## Confirmation requested

1. Approve this phase order?
2. Approve continuing ADR from the existing local `docs/adr/` set (2.3)?

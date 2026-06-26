# Execution Plan — derived from approved requirements.md

> Author: Andy · Status: DRAFT for 启鸣 confirmation
> Basis: `requirements.md` (approved 2026-06-26). This plan sequences R1–R10 into ordered, owned steps with gates.
> Legend — Owner: **启鸣** (human) / **Andy** (chat) / **CC** (Claude Code, local).

---

## Phase 0 — Security & guardrails (do before any code work)

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 0.1 | Revoke the leaked over-privileged token | 启鸣 | Old token returns 401 |
| 0.2 | Reissue fine-grained PAT: `cineanchor-neo` only, Contents R/W, with expiry | 启鸣 | New token handed over off-log |
| 0.3 | Protect `main`: Require PR + Block force pushes | 启鸣 | `main` shows `protected: true` |

**Phase 0 is blocking.** Until 0.3 is done, the "never touch main" rule has no hard enforcement.

---

## Phase 1 — Establish the workflow (process, no product code)

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 1.1 | Adopt `workflow_rules.md` (this branch) as the binding ruleset | 启鸣 | 启鸣 approves the rules file |
| 1.2 | Append two-agent role split (R1) into `.claude/CLAUDE.md` | CC | 启鸣 reviews diff |
| 1.3 | Confirm handoff protocol (R4): Andy → `Andy` branch → 启鸣 review | Andy/启鸣 | This very loop proves it works |

---

## Phase 2 — Knowledge docs (lightweight, under `docs/`)

Build in this order — boundary first (highest value), then map, then decisions.

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 2.1 | `docs/scope.md` (R8): consolidate do/don't from AGENTS.md + CLAUDE.md | CC drafts, Andy reviews | 启鸣 approves; no out-of-scope items leak |
| 2.2 | `docs/codemap.md` (R9): one-page module map + call flow | CC drafts, Andy reviews | Map matches actual tree; shallow, regenerate-on-change |
| 2.3 | `docs/ADR/` (R10): reconcile with 启鸣's existing local ADR | **BLOCKED** on 启鸣 sending local `docs/ADR` address | Existing ADRs merged, not forked |

**2.3 is blocked** until 启鸣 provides the local `docs/ADR` address (per requirements R10).

---

## Phase 3 — Execution loop becomes live

Once Phases 0–1 are done, the standing loop for every requirement is:

```
启鸣 states need
  → Andy clarifies + writes requirements/acceptance to `Andy` branch
  → 启鸣 reviews/approves on `Andy` branch
  → CC reads approved doc, runs PLAN MODE, writes plan
  → 启鸣 reviews plan  →  Andy reviews plan   (R5 double-review gate)
  → both pass → CC executes on a spike/* or feature/* branch
  → if output is video: CC renders locally, outputs test video PATH (R6)
  → 启鸣 accepts video → CC opens PR to main → 启鸣 merges (R2)
```

| # | Step | Owner | Gate / Done-when |
|---|------|-------|------------------|
| 3.1 | Add lightweight pre-push smoke check (R7) | CC | Hook runs frame-count / black-frame / MP4-plays check |
| 3.2 | Run first real requirement end-to-end through the loop | all | One video accepted + merged via PR |

---

## Deferred (unchanged from requirements.md)

- 历史口径 — no history yet; defer.
- Separate LLM Wiki — covered by CLAUDE.md + ADR.
- Path-allowlist CI (②) / CODEOWNERS (③) — dropped by choice; residual exposure accepted (main protection is the backstop).

---

## Critical path

`0.1–0.3 (security)` → `1.1 (rules approved)` → `2.1 scope` → loop goes live.
ADR (2.3) and codemap (2.2) can proceed in parallel once 启鸣 unblocks the ADR address.

## Confirmation requested

1. Approve this phase order?
2. Confirm Phase 0 is yours to action (token + main protection) before code work starts.
3. Send the local `docs/ADR` address to unblock 2.3.

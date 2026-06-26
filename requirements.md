# Collaboration Workflow Requirements — Now-Executable Items

> Author: Andy (chat agent) · Status: DRAFT for 启鸣 confirmation
> Scope: Solo dev + two-agent workflow setup.
> Source: deconstruction of "如何搭建一个端到端业务需求专家 Agent", filtered for solo-dev fit.

This document lists the items classified as "now-executable" (现在就能做).
Deferred / unsuitable items are listed at the bottom so expectations are clear.

> **Note on Spike rules:** `AGENTS.md` currently discourages creating `docs/` trees during Spike.
> 启鸣 has explicitly chosen to include the knowledge docs (scope / codemap / ADR) now.
> They are kept lightweight and live under `docs/`, separate from disposable Spike code.

---

## R1. Two-agent role split (process only, no code)

- **Andy (chat)** = upstream product brain: requirement intake, clarification, decisions, acceptance criteria, code/plan review.
- **Claude Code (local machine)** = executor: reads `.claude/CLAUDE.md` + `AGENTS.md`, runs plan mode, writes code, renders video locally.
- **启鸣** = sole approver of every gate.
- **Why now:** zero code, zero infra. It is the backbone everything else hangs on.
- **Deliverable:** one short section appended to `.claude/CLAUDE.md` describing the split (done by Claude Code after approval).

## R2. main branch protection — the real "never touch main" enforcement

- **Current state: main is NOT protected.** Any token (including Andy's) can push straight to main. The "Andy only writes the `Andy` branch" rule is currently a convention with no hard backing.
- **Action:** enable on `main` — *Require a pull request before merging* + *Block force pushes*.
- **Why now:** this is the ONLY mechanism that physically prevents anything (Andy, Claude Code, or a leaked token) from reaching main without your PR merge. Branch naming is a label; main protection is the wall.
- **Deliverable:** you flip the GitHub setting (1 minute). Out of the agreed ①+④ scope for Andy to do automatically.

## R3. Token hardening (security, urgent)

- **The token shared is over-privileged:** *admin on 7 repos*, and it was posted in plaintext chat.
- **Action:** (1) revoke the current token; (2) reissue a fine-grained PAT scoped to `cineanchor-neo` only, *Contents: Read/Write* only, with an expiry; (3) hand it over through a non-logged channel if possible.
- **Why now:** matches the agreed token-constraint design (layer ④ = narrow the token; layer ① = Andy works only in branch sandboxes). Without this, ④ is not actually in effect.

## R4. Requirements / plan handoff protocol (this very doc is the first instance)

- **Flow:** Andy writes a markdown doc (requirements / acceptance criteria) → pushes to the `Andy` branch → you review → you decide whether it goes to Claude Code.
- **Rule:** Andy writes **only** to the `Andy` branch, never to `main`, `spike/*`, or `feature/*`.
- **Why now:** lightweight, async, leaves a reviewable trail. No CI, no CODEOWNERS needed (layers ② and ③ dropped).
- **Deliverable:** this `requirements.md` on a clean `Andy` branch.

## R5. Plan-mode + double-review gate before execution

- **Flow:** Claude Code reads approved requirements → produces a plan in plan mode → **you review** → **Andy reviews** → only if both pass does Claude Code execute.
- **Why now:** process only. Catches scope creep before code is written.
- **Note:** keep it lightweight — a plan can be a few bullet points, not a full design doc.

## R6. Video acceptance loop (human-in-the-loop, mandatory)

- **Rule:** any requirement loop that produces a video MUST be rendered locally by Claude Code, which outputs the **test video file path** for you to review. Andy cannot render (no Blender/FFmpeg in its sandbox).
- **Why now:** the product's final output is video; only a human can judge it. Already approved.

## R7. Lightweight pre-push smoke check (optional, light-grade)

- **Action:** a minimal pre-push hook that runs whatever smoke check exists (e.g. "render produced N frames, no black frames, MP4 plays"). NOT a full TDD hard gate yet.
- **Why now-but-light:** treat current code as still-evolving. Upgrade to a hard gate when entering V0.1.

## R8. System boundary doc — `docs/scope.md` (系统边界)

- **Action:** extract and consolidate the "do / don't" boundary into `docs/scope.md`: what CineAnchor does (PNG/GLB → template → 1080p MP4) and explicit non-goals (no preview parity, no BGM auto, no cloud/SaaS, no account system, ComfyUI conservative-only, serial render, local-only).
- **Source:** lift from `AGENTS.md` "Non-Goals Before V1.0" + `.claude/CLAUDE.md` constraints into one canonical reference.
- **Why now:** prevents Andy and Claude Code from "helpfully" adding out-of-scope features. The single highest-value knowledge doc for a solo dev.

## R9. Code map — `docs/codemap.md`

- **Action:** a one-page module map: each significant file/folder, its responsibility, and call relationships (e.g. web entry → FastAPI route → Blender render script → FFmpeg → MP4).
- **Why now:** lets Andy and Claude Code locate code without re-reading the whole tree each time.
- **Note:** keep it shallow and regenerate-on-change; Claude Code can auto-update it when it touches code.

## R10. ADR — `docs/ADR/` (Architecture Decision Records)

- **Action:** record tech-selection decisions as numbered ADRs (status: proposed / accepted / superseded). Each ADR = context, decision, alternatives considered, consequences.
- **Reconcile first:** 启鸣 already has a local `docs/ADR`. **Await the local address before writing** so we merge with the existing set instead of forking it.
- **Why now:** the correct durable form of knowledge during tech selection — captures *why* a route was chosen without locking code.

---

## Deferred / Not-now (so scope is explicit)

- **历史口径 (historical metric definitions)** — no history accumulated yet; nothing to align. Defer.
- **Separate LLM Wiki** — for a solo project, `.claude/CLAUDE.md` + ADR already serve this role. Do not build a separate wiki.
- **Path-allowlist CI (layer ②) / CODEOWNERS (layer ③)** — dropped by choice. Residual exposure accepted: the token can write content to non-main branches, but main protection (R2) keeps the trunk safe and every change stays a reviewable diff.

---

## Confirmation requested

Please confirm:
1. Is this "now-executable" list correct and complete?
2. Do you accept the residual exposure noted under R3 / deferred section (only layers ① + ④)?
3. For R10 ADR — send the local `docs/ADR` address so Andy reconciles instead of forking.
4. Should Andy proceed to draft the `.claude/CLAUDE.md` role-split section (R1) next, or adjust first?

This file lives only on a clean `Andy` branch (orphan, no `main` files). Nothing written to `main`.

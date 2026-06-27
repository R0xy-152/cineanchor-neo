# Base Rules — Workflow & GitHub Modification

> Author: Andy · Status: DRAFT for 启鸣 confirmation
> Binding ruleset for the CineAnchor Neo two-agent collaboration. Supersedes ad-hoc conventions.
> Note: Phase 0 security & guardrails (token hardening, main-branch protection) are out of scope per 启鸣's decision (2026-06-27).

---

## 1. Roles & authority

| Role | Who | May do | May NOT do |
|------|-----|--------|------------|
| Approver | **启鸣** | Approve requirements, plans, video acceptance; merge PRs to main | — |
| Product brain | **Andy** (chat) | Write requirements / acceptance / review docs to the `Andy` branch | Touch `main`, `spike/*`, `feature/*`; render video; merge PRs |
| Executor | **Claude Code** (local) | Write code on `spike/*` / `feature/*`; render video; open PRs | Merge to `main`; bypass plan-mode/double-review |

**启鸣 is the sole merge authority.** No agent merges to `main`.

---

## 2. Branch rules

| Branch | Purpose | Who writes | Merge into main |
|--------|---------|-----------|-----------------|
| `main` | Stable only | nobody directly | via PR, 启鸣 merges |
| `Andy` | Andy's requirement/plan/review docs + ADR management under `docs/adr/` | Andy | never auto; cherry-pick if needed |
| `spike/*` | Spike validation code (disposable) | CC | only if promoted, via PR |
| `feature/*` | Product feature work (post-Spike) | CC | via PR |
| `docs/*` | Documentation / portfolio | CC or Andy | via PR |

- **Naming:** use `-` separators, never `/` inside a segment beyond the prefix (Docker-tag safety).
- **Andy writes only to the `Andy` branch.** This is a followed convention (no hard enforcement, since main protection is out of scope).
- **ADR ownership:** Andy manages ADRs directly on the `Andy` branch under `docs/adr/`. This is the one code-tree area Andy maintains (the `docs/adr/` set was synced here by Claude Code for this purpose). Andy still does not write other `docs/` files or any source code.

---

## 3. GitHub modification rules

1. **Never push directly to `main`.** All `main` changes go through a PR that 启鸣 merges.
2. **Andy writes only to the `Andy` branch**, only markdown docs (requirements / plan / review). Andy never edits code files.
3. **One logical change per commit.** No drive-by edits to unrelated files.
4. **Read before write.** Read the full current file before modifying; make targeted edits, never blind full-file overwrites.
5. **Verify after write.** Re-fetch the file / check the diff after pushing; if deletions vastly exceed additions, stop and flag.
6. **Commit / MR naming:** `type(scope): short description`. Andy's commits/MRs are prefixed `[Andy]`.
   - Examples: `[Andy] docs: add requirements`, `feat(render): add dolly_out camera`.
7. **No force-push to shared branches.** Force-push only your own throwaway branch, never another agent's.
8. **Don't bypass agreed rules.** If blocked by a rule, escalate to 启鸣 rather than working around it.

---

## 4. Execution workflow (standing loop)

```
1. 启鸣 states a need
2. Andy clarifies, writes requirements + acceptance criteria → `Andy` branch
3. 启鸣 reviews on `Andy` branch → approve / revise
3b. On approval, Andy runs the ADR evaluation (see §8); if triggered, drafts a new ADR
4. Claude Code reads approved doc → PLAN MODE → writes plan
5. Double-review gate: 启鸣 reviews plan AND Andy reviews plan
6. Both pass → CC executes on spike/* or feature/*
7. If output is video: CC renders locally, outputs the test video FILE PATH
8. 启鸣 reviews the video (only a human accepts video)
9. CC opens PR → 启鸣 merges to main
```

- **No step skipped.** Plan-mode and the double-review gate are mandatory before code is written.
- **Keep it light during Spike:** a plan can be a few bullets; smoke checks over full TDD.

---

## 5. Safety rules (hard, never bypass)

- **Deletion:** confirm intent before deleting anything. Shared/others' resources need explicit 启鸣 approval.
- **Scope discipline:** do only what the approved doc specifies. No out-of-scope "improvements" (see `docs/scope.md` once it exists).
- **Code safety:** read full file → targeted edit → verify diff → never delete functional code unasked.
- **Secrets:** never commit tokens / credentials into any file.

---

## 6. File naming (Andy branch)

The `Andy` branch holds only review / handoff markdown docs. Naming rule:

**Standing docs (cross-loop governance):**
```
00-<name>.md
```
- `00-` prefix sorts them to the top; names are stable.
- Example: `00-workflow-rules.md`

**Per requirement loop:**
```
<NN>-<slug>-<type>.md
```
- `NN` = two-digit zero-padded loop sequence (`01`, `02`, …; widen all numbers together when exceeding 99).
- `slug` = concise kebab-case topic.
- `type` = `requirements` | `plan` | `review` | `acceptance` (vocabulary is extensible).
- Examples: `01-workflow-setup-requirements.md`, `01-workflow-setup-plan.md`

**Why this scheme:**
- *Readability:* the numeric prefix groups all files of one loop together when sorted; the `type` suffix shows a file's purpose at a glance.
- *Extensibility:* new loops just increment the number; new document kinds extend the `type` vocabulary; if a loop ever accumulates many files, it upgrades cleanly to a sub-folder form `NN-<slug>/<type>.md` without breaking the convention.

---

## 7. Language (CN / EN)

- **Requirements / acceptance docs (for 启鸣 to review) → Chinese.** These are human-decision documents; Chinese lowers reading cost.
- **Plan / execution / technical docs (codemap, rules, ADR consumed by Claude Code) → English.** Agent/execution-facing; English is more token-efficient and consistent with the code.
- **Quick reference:** `*-requirements.md` = 中文; `*-plan.md`, `00-*` rules, `docs/*` technical = English.

---

## 8. ADR evaluation after requirements approval

Every time a `requirements` doc is approved, Andy MUST run this evaluation before handing off to Claude Code:

1. **Does this requirement involve a product decision?** (e.g. choosing a tech route, changing the JSON schema/contract, adding/dropping a capability, a trade-off with lasting consequences — not a pure chore or doc edit.)
2. **Is it worth persisting into `docs/adr/`?** (i.e. future-you would ask "why did we decide this?" — not a throwaway Spike experiment.)

**If BOTH are true → draft a new ADR.**
- Continue numbering from the existing local set (latest is `ADR-004`), so the next is `ADR-005-<slug>.md`.
- ADR body: context · decision · alternatives considered · consequences · status (proposed/accepted/superseded).
- Authoring path: Andy writes the ADR markdown directly into `docs/adr/` on the `Andy` branch (Andy owns the ADR set here). 启鸣 reviews on the `Andy` branch; promotion to `main` still goes through the normal PR → 启鸣 merge flow.

**If either is false → skip; record nothing.** Most chores, doc-only changes, and disposable Spike probes will not trigger an ADR.

---

## Confirmation requested

1. Adopt this as the binding ruleset?
2. Any rule to tighten/loosen (esp. branch table, Andy's markdown-only limit, the naming scheme)?

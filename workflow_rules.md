# Base Rules — Workflow & GitHub Modification

> Author: Andy · Status: DRAFT for 启鸣 confirmation
> Binding ruleset for the CineAnchor Neo two-agent collaboration. Supersedes ad-hoc conventions.

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
| `Andy` | Andy's requirement/plan/review docs only | Andy | never auto; cherry-pick if needed |
| `spike/*` | Spike validation code (disposable) | CC | only if promoted, via PR |
| `feature/*` | Product feature work (post-Spike) | CC | via PR |
| `docs/*` | Documentation / portfolio | CC or Andy | via PR |

- **Naming:** use `-` separators, never `/` inside a segment beyond the prefix (Docker-tag safety).
- **Andy is hard-limited to the `Andy` branch.** This is convention; the real wall is `main` protection.

---

## 3. GitHub modification rules

1. **Never push directly to `main`.** All `main` changes go through a PR that 启鸣 merges.
2. **Andy writes only to the `Andy` branch**, only markdown docs (requirements / plan / review). Andy never edits code files.
3. **One logical change per commit.** No drive-by edits to unrelated files.
4. **Read before write.** Read the full current file before modifying; make targeted edits, never blind full-file overwrites.
5. **Verify after write.** Re-fetch the file / check the diff after pushing; if deletions vastly exceed additions, stop and flag.
6. **Commit / MR naming:** `type(scope): short description`. Andy's commits/MRs are prefixed `[Andy]`.
   - Examples: `[Andy] docs: add requirements.md`, `feat(render): add dolly_out camera`.
7. **No force-push to shared branches.** Never force-push `main`. Force-push only your own throwaway branch, never another agent's.
8. **No editing branch protection or merge config** to bypass a rule. If blocked, escalate to 启鸣.

---

## 4. Execution workflow (standing loop)

```
1. 启鸣 states a need
2. Andy clarifies, writes requirements + acceptance criteria → `Andy` branch
3. 启鸣 reviews on `Andy` branch → approve / revise
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
- **Secrets:** never commit tokens/credentials. If a secret is exposed (e.g. token in chat), flag immediately and require rotation.

---

## 6. Token & access

- Andy uses a fine-grained PAT scoped to `cineanchor-neo`, Contents R/W only, with expiry.
- The token cannot restrict which branch it writes — branch safety comes from `main` protection, not the token.
- Rotate the token on any exposure. Andy's writes are confined to the `Andy` branch by convention + reviewed by 启鸣.

---

## Confirmation requested

1. Adopt this as the binding ruleset?
2. Any rule to tighten/loosen (esp. branch table and Andy's markdown-only limit)?

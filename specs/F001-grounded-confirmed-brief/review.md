# Review Record: F001 Grounded Confirmed Brief

- Reviewer: implementing agent (self review), 2026-08-24
- Scope: commits `66ec420` (T0/T1) through `7004699` (T11)
- Gate revisions reviewed: SPEC `d7ae5094c490`, UX/UI `c4cd127cb372`, TEST DESIGN `dc6978dfefc8`, PLAN `plan-f001-r1` (+ in-place task checkboxes)

## Verification evidence

- Backend: 51 tests green (identity, projects, sources, standards, discovery, streaming, brief, deletion, trace, health); ruff check/format clean.
- Frontend: 11 component tests green; eslint/tsc/prettier clean; production build passes.
- E2E: Playwright public entry, auth guard, keyboard focus 3/3 pass; authenticated happy path gated (`CLERK_E2E=1`) pending external Clerk setting.
- Live checks: `/health` against compose services `{"status":"ok","database":"ok"}`; web home renders; Clerk sign-in widget loads and accepts credentials up to device verification.

## Findings

| Severity | Finding | Disposition |
| --- | --- | --- |
| Critical | none | — |
| High | none | — |
| Medium | Authenticated E2E (TS-024/025) cannot run while Clerk "new device verification" is enabled on the dev instance; automated sign-in blocked at client-trust. | Spec present, gated; deterministic coverage via component + API tests; unblock by disabling the Clerk setting, then run `CLERK_E2E=1`. |
| Medium | Capped live DeepSeek smoke (T5) not recorded; no DeepSeek API key provided. | RESOLVED 2026-08-24: key provided; live smoke recorded — `complete` 2640ms, 31 prompt + 3 completion tokens; `stream` yields tokens correctly. Two capped calls total. |
| Low | In-progress narration buffer is process-local; reconnect after completion is durable (persisted message), mid-stream reconnect across processes is not. | Accepted for F001 single-instance dev; document before multi-worker deployment. |
| Low | Source-count quota is checked then inserted (non-atomic under true concurrency). | Accepted for single-teacher demo; DB-level enforcement revisited with F011 quotas. |

## Spec compliance spot checks

- AC-001/002/003: workspace bootstrap once, owner CRUD, cross-account non-disclosure (tests + live widget).
- AC-004/005/006: format/size/count policy, student-data rejection before grounding, lifecycle states.
- AC-007/008/009: gap-only questions, 6x3 cap with unresolved markers, stop preserves completing call + full trace, re-ask quota-counted.
- AC-010..013: grounding markers, stale 409, confirm 422 missing fields, immutable idempotent confirm.
- AC-014: standards snapshot citations with version; hostile content inert.
- AC-015/016: cascade deletion with audit + retryable failure; purge-then-Clerk ordering with recorded failures.
- AC-017/018: provider failure preserves state, retry resumes; SSE reconnect replays without new model work.
- AC-019: desktop gating for structured tasks; read-only + conversational on small screens.

## Conclusion

No Critical or High findings. Two Medium findings are external-evidence gaps with deterministic fallbacks and explicit unblock paths. Recommend `Roadmap Status: REVIEW` and `READY FOR PR` pending PR authorization.

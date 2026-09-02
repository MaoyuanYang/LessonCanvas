# Remove Managed Identity (Clerk) for the MVP; Application-Issued Anonymous Workspace Tokens Without Login

- Status: `Accepted`
- Date: 2026-09-02
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: Supersedes the identity-provider selection recorded in F001 Spec D1 (Clerk) and the identity item of the F011 D10 provider constraint set; those Feature records remain immutable history.

## Context

Phase 1 uses Clerk as the managed identity provider (F001 D1): the web signs in through Clerk, the backend validates Clerk JWTs via JWKS, and account deletion calls the Clerk user-deletion API. In practice the Clerk dependency repeatedly blocked the portfolio workflow: intermittent dev-instance session hangs (F004/F005 E2E residuals), device-verification friction (disabled by the owner to unblock E2E), and an owner-managed allowed-origin prerequisite on the deployed LAN entry (F012 B-003). The product has no real user base in Phase 1; the portfolio needs an inspectable deployed demo, not a production identity system. The owner decided the MVP drops login/logout entirely.

Removing identity outright is not viable: ownership, F011 quotas/rate limits, isolation, and deletion are all keyed to a workspace subject. The backend already carries a second, deterministic token path (HS256 dev verifier), which every deterministic test already uses.

## Decision

- Phase 1 removes Clerk entirely: no login/logout UI, no third-party identity dependency, no Clerk admin API calls.
- Identity becomes an application-issued anonymous workspace token: `POST /auth/guest-token` mints an HS256 token with a fresh random subject (30-day expiry) signed by the application secret; the web stores it in `localStorage` and attaches it as the existing `Authorization: Bearer` header. Each browser is one isolated workspace; all F011 ownership, quota, rate, isolation, and deletion behavior is preserved unchanged on the subject key.
- No password storage, credential handling, or account-recovery surface exists; AGENTS' rule that the Identity module never owns password storage still holds.
- The workspace subject columns are renamed from the Clerk-era `clerk_user_id` to `subject` so the schema matches the model.
- Account deletion stops after the application-side purge; the external identity-step statuses disappear.
- Revisit trigger: before any real public multi-user rollout beyond the owner-controlled LAN demo (or whenever accounts, recovery, or anti-abuse beyond F011 guardrails become requirements), managed identity must be reintroduced and this ADR superseded.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Keep Clerk | Managed identity already integrated; no L3 change | Recurring friction blocking the portfolio; unnecessary for a zero-user MVP; extra provider prerequisite for deployment |
| Single shared demo workspace, no tokens | Simplest UX | Destroys F011 workspace isolation, quota, and deletion evidence; misrepresents the architecture |
| Pre-shared fixed tokens distributed by the owner | No issuance endpoint | Poor reviewer experience; manual distribution; no per-browser isolation |
| Cookie-based sessions | Transparent to JS | Cross-origin web/API split needs credentialed CORS; more churn than the existing header seam |

## Consequences

- The web has no sign-in route or auth middleware; protected pages degrade to in-app `AUTH_REQUIRED` states instead of login redirects.
- Losing the `localStorage` token (cleared browser data) starts a new empty workspace; prior data remains server-side and deletable per project, but is not re-linkable. Accepted for the MVP demo.
- E2E journeys become fully deterministic (no third-party sign-in), resolving the F011 M-1 env-gated residual pattern.
- Historical Feature records (F001 D1, F011 D10) keep describing Clerk as built; this ADR records the supersession.

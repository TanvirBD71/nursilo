# Nursilo — Frontend State Management Architecture

| Field | Value |
| --- | --- |
| Document | `23-frontend-state-management-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`22`](22-frontend-error-recovery-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual classification, ownership, transfer, presentation, synchronization, and recovery of frontend state for Nursilo V1 |
| Out of scope | Redux/Zustand/SPA stores; HTML; CSS; JS source; Alpine/HTMX source; APIs; databases; infrastructure; implementation artifacts |
| Nature | **Additive only** — does not modify locked docs `00`–`22`. |

---

## 1. Metadata

See table above. This is **not** a client state-library proposal. Nursilo V1 remains **server-rendered first** ([`13`](13-frontend-architecture.md)).

---

## 2. Purpose

Prevent accidental creation of a client-side source of truth. State is classified, owned, and synchronized so the browser displays and requests—never authorizes, entitles, scores, or confirms payment.

```text
04 System Architecture / 09 Business Rules
    ↓
13–18 Frontend / 19–22 drafts
    ↓
23 State Management Architecture
    ↓
Future implementation
```

---

## 3. Relationship to docs/04, 09, 13–22

| Document | Role |
| --- | --- |
| [`04`](04-system-architecture.md) | Presentation → application/domain services |
| [`09`](09-business-rules.md) | Domain state machines / outcomes |
| [`13`](13-frontend-architecture.md)–[`18`](18-frontend-interaction-architecture.md) | Rendering & interaction model |
| [`19`](19-frontend-form-validation-architecture.md) | Form state (draft) |
| [`20`](20-frontend-accessibility-architecture.md) | A11y state expectations (draft) |
| [`21`](21-frontend-performance-architecture.md) | Async efficiency (draft) |
| [`22`](22-frontend-error-recovery-architecture.md) | Error state & recovery (draft) |

---

## 4. State Management Principles

| Principle | Meaning |
| --- | --- |
| Server truth | Confirmed outcomes from server |
| Minimal client state | Local UI only where temporary |
| Explicit ownership | Every state has an owner |
| Predictable transitions | Named, visible changes |
| Progressive enhancement | Works without heavy client stores |
| No duplicated business rules | Rules stay in domain/services |
| Recoverability | Align with docs/22 |
| Accessibility / localization / consistency | Cross-cutting |

---

## 5. State Ownership Model

### Server-authoritative state

Authentication; authorization; role; entitlement; subscription; payment; assessment attempt; timer truth; answers; scoring; completion; workflow status; persistence.

### Presentation state

Labels; display modes; server-provided status; page metadata; permission-aware visibility already decided by server.

### Local UI state

Dropdown open; modal open; tab; disclosure; password visibility; temporary selection; temporary visual preferences.

### Request state

Idle; loading; submitting; success; failure; retry.

---

## 6. State Classification Matrix

| State | Owner | Persistence | Authority | Example |
| --- | --- | --- | --- | --- |
| Authentication | Server | Session store | Server | Logged in / expired |
| Entitlement | Server | Billing/entitlement services | Server | Free / Premium / Locked |
| Payment | Server | Payment records | Server | Pending / Confirmed / Failed |
| Attempt | Server | Attempt aggregate | Server | InProgress / Completed |
| Timer truth | Server | Attempt timing | Server | Remaining time |
| Answers | Server | Attempt items | Server | Saved selection |
| Score / completion | Server | Scoring rules | Server | Result view |
| Workflow status | Server | Editorial rules | Server | Draft → Published |
| Form field values (unsaved) | Browser (temp) | None until submit | Server after save | Editing profile |
| Modal open | Browser | None | Local UI only | Dialog visible |
| Request loading | Browser + server response | Ephemeral | Server result wins | Submitting form |
| Read/unread notification | Server | Notification store | Server | Mark read |
| Bookmark | Server | Bookmark store | Server | Bookmarked |

---

## 7. Server State

Server-provided state is authoritative. The frontend must re-fetch or accept server responses after mutations. Client claims alone never establish access or outcomes ([`07`](07-security-and-session-management.md)).

---

## 8. Presentation State

Server state is mapped into display state by the presentation boundary: safe labels, statuses, actions/URLs, and visibility flags. Templates/components render presentation state; they do not compute business outcomes.

---

## 9. Local UI State

Safe for temporary presentation only. Must reset harmlessly. Must not imply auth, entitlement, score, payment, or workflow success.

---

## 10. Request / Async State

Align with [`18`](18-frontend-interaction-architecture.md) and [`21`](21-frontend-performance-architecture.md): idle → loading → success/failure; avoid chatty loops; no indefinite loading masking errors.

---

## 11. Form State

Align with [`19`](19-frontend-form-validation-architecture.md): initial; editing; dirty; submitting; validation error; success/failure. Server validation authoritative.

---

## 12. Accessibility State

Align with [`20`](20-frontend-accessibility-architecture.md): focus location, expanded/collapsed, announced status—presentation aids, not security.

---

## 13. Error State

Align with [`22`](22-frontend-error-recovery-architecture.md): failure presentation and recovery paths without false success.

---

## 14. Assessment State

Explicit separation:

| Concern | Authority |
| --- | --- |
| Attempt truth | Server |
| Timer truth | Server |
| Answer truth | Server |
| Question version | Server |
| Submission truth | Server |
| Score | Server |
| Completion | Server |

Browser may display and request transitions only. Resume/complete/auto-submit behavior follows [`09`](09-business-rules.md).

---

## 15. Learning State

Current lesson presentation; progress presentation; completion; continue learning—mutations server authoritative.

---

## 16. Library / Reader State

Access; bookmark; reading position where applicable; download status—access and persistence server authoritative; storage keys are not auth.

---

## 17. Subscription / Payment State

Current plan; entitlement; pending; success; failure—server authority. No client-confirmed Premium.

---

## 18. Notification State

Read/unread belongs to server. No fake unread counts.

---

## 19. Staff / Admin State

RBAC, workflow, and persistence belong to server. Dense UI may hold temporary selection for bulk actions until server confirms.

---

## 20. State Synchronization

```text
Server → Presentation
User action → Request
Server result → Updated presentation state
```

---

## 21. Stale State

Stale UI; stale records; concurrent changes; conflict; refresh/reload; server reconciliation.

Do not invent conflict rules—present server conflict outcomes from [`09`](09-business-rules.md) / services.

---

## 22. Optimistic UI Boundary

| May be acceptable (cosmetic) | Forbidden optimistic assumptions |
| --- | --- |
| Brief local pending on low-risk toggles if immediately reconciled | Payment success |
| | Entitlement grant |
| | Assessment submission / score |
| | Authentication / authorization |
| | Workflow authority (publish/approve) |

If uncertain, wait for server.

---

## 23. HTMX State Boundary

Partials replace presentation from server HTML/state. Failed swaps must not leave invented success ([`22`](22-frontend-error-recovery-architecture.md)).

---

## 24. Alpine State Boundary

Local UI only. Never persistence, auth, entitlement, score, payment, or workflow truth.

---

## 25. Navigation State

Major IA/security/assessment/payment transitions prefer full navigation for clean state ([`15`](15-frontend-page-architecture.md), [`18`](18-frontend-interaction-architecture.md)).

---

## 26. Modal / Disclosure State

Local open/close; content loaded from server when needed; restore focus on close.

---

## 27. Loading State

Ephemeral request presentation; not a business outcome.

---

## 28. Empty State

Server-confirmed empty collections; helpful next actions; not an error unless server says so.

---

## 29. Error State

See [`22`](22-frontend-error-recovery-architecture.md).

---

## 30. State Data Contracts

Presentation receives: current values; statuses; allowed actions/URLs; messages; a11y metadata; localization. No repository access from UI state layer.

---

## 31. Security Boundary

Browser state is untrusted. Hidden/disabled controls are not protection. Details in [`24`](24-frontend-security-trust-boundary-architecture.md).

---

## 32. Accessibility Boundary

State changes that matter must be perceivable ([`20`](20-frontend-accessibility-architecture.md)).

---

## 33. Localization Boundary

State labels/messages support Bangla/English expansion.

---

## 34. Performance Boundary

Minimize unnecessary state churn and requests ([`21`](21-frontend-performance-architecture.md)).

---

## 35. Testing Strategy

Ownership tests conceptually: server vs local; no optimistic forbidden domains; sync after mutation; stale/conflict presentation; assessment/payment/auth state; regression.

---

## 36. Naming Conventions

| Good | Avoid |
| --- | --- |
| AttemptStatus, EntitlementState, RequestLoading, ModalOpen | GlobalStore, MagicState, TempTruth |

---

## 37. Reuse Rules

Reuse state patterns; do not create parallel client stores for server domains.

---

## 38. Governance

Prevent SPA-store creep; review new state owners; locked docs win conflicts.

---

## 39. Future-only Extensions

**Future-only:** Offline Mode local caches; Flutter client state; real-time sync stores; AI Tutor session state.

---

## 40. Cross References

[`04`](04-system-architecture.md), [`07`](07-security-and-session-management.md), [`09`](09-business-rules.md), [`13`](13-frontend-architecture.md)–[`22`](22-frontend-error-recovery-architecture.md).

**This document does not modify any approved or draft predecessor.**

---

## 41. Acceptance Criteria

Accept when ownership model, classification matrix, server/presentation/local/request states, domain states (assessment/learning/library/payment/notification/staff), sync/stale/optimistic boundaries, HTMX/Alpine/nav/modal/loading/empty/error, contracts, security/a11y/i18n/performance boundaries, testing, naming, reuse, governance, and Future-only extensions are defined; no client source-of-truth architecture introduced; docs `00`–`22` unchanged by this file’s creation.

---

## 42. Document Lock

**Status:** `docs/23-frontend-state-management-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend state management architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`22` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

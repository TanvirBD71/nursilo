# Nursilo — Frontend Error & Recovery Architecture

| Field | Value |
| --- | --- |
| Document | `22-frontend-error-recovery-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`21`](21-frontend-performance-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual architecture for frontend error handling, recovery, failure communication, retry behavior, and safe recovery paths for Nursilo V1 |
| Out of scope | HTML; CSS; Tailwind; JavaScript; Alpine; HTMX attributes; Django templates; Python; API schemas; database; infrastructure; Figma; implementation artifacts |
| Nature | **Additive only** — does not modify locked docs `00`–`21`. |

---

## 1. Document Metadata

See table above. This document defines **how failures are presented and recovered** at the frontend boundary. It does not invent business, scoring, payment, or entitlement rules.

---

## 2. Purpose

Every failure must produce a predictable, accessible, secure, recoverable experience. Displaying an error message is not enough: users need a safe next action, and the UI must never invent success.

```text
07 Security / 09 Business Rules (authority)
    ↓
13–18 Frontend layers / 19–21 drafts
    ↓
22 Error & Recovery Architecture
    ↓
Future implementation
```

---

## 3. Relationship to docs/07, 09, 11, 13–21

| Document | Role |
| --- | --- |
| [`07`](07-security-and-session-management.md) | Session, CSRF, re-auth, security messaging authority |
| [`09`](09-business-rules.md) | Assessment, payment, entitlement, workflow conflict authority |
| [`11`](11-ui-ux-specification.md) | Experience expectations for failure UX |
| [`13`](13-frontend-architecture.md)–[`18`](18-frontend-interaction-architecture.md) | Tech, page, template, style, interaction boundaries |
| [`19`](19-frontend-form-validation-architecture.md) | Form validation / field error presentation (draft) |
| [`20`](20-frontend-accessibility-architecture.md) | Accessibility error contract (draft) |
| [`21`](21-frontend-performance-architecture.md) | Fail-fast / no request storms (draft) |

On conflict: **locked docs win**.

---

## 4. Error Architecture Principles

| Principle | Meaning |
| --- | --- |
| Server truth | Outcome comes from the server |
| Clear communication | User understands what failed |
| Recoverability | Understandable next action when possible |
| Security-safe messaging | No secrets, stack traces, or enumeration leaks |
| Accessibility | Errors perceivable via keyboard/SR/focus |
| Localization | Bangla / English / mixed-language safe |
| Progressive enhancement | Base forms/links still recover |
| Predictable states | Explicit failure → recovery → stable |
| No hidden failures | Silent wrong state is forbidden |
| No false success | Especially payment and assessment submit |
| No client-side business authority | No scoring/entitlement/RBAC in browser |

---

## 5. Error Taxonomy

Conceptual categories (not HTTP catalogs):

| Category | Meaning |
| --- | --- |
| Validation error | Input fails server validation |
| Authentication error | Credentials/session identity failed |
| Authorization error | Authenticated but not permitted |
| Entitlement error | Free/Premium/locked access denied |
| Session expiration | Session no longer valid |
| Not found | Resource unavailable to this viewer |
| Conflict | Business/state conflict from server |
| Stale state | UI or attempt no longer current |
| Network failure | Request did not complete |
| Timeout | Request exceeded wait |
| Server failure | Unexpected server error |
| Maintenance | Planned unavailability |
| Unavailable content | Content not available |
| Upload failure | File upload rejected/failed |
| Payment failure | Payment not confirmed / failed |
| Assessment failure | Attempt/answer/submit/timer issues |
| Workflow failure | Editorial/ops transition rejected |

Do not invent API status codes here.

---

## 6. Error Severity Model

| Severity | Use |
| --- | --- |
| Informational | Non-blocking notice |
| Recoverable | User can retry/edit/continue safely |
| Blocking | Flow cannot continue until resolved |
| Security-sensitive | Auth/session/security actions |
| System-critical | Maintenance / widespread outage |

This is a **presentation** severity model. It is not a second business-rule authority.

---

## 7. Error State Lifecycle

```text
Trigger
→ Loading
→ Failure
→ Presentation
→ Recovery
→ Retry / safe exit
→ Stable state
```

---

## 8. Error Presentation Architecture

| Placement | When |
| --- | --- |
| Inline / field-level | Validation association |
| Form-level | Summary of form failures |
| Section-level | Partial region failures |
| Page-level | Workflow / auth / payment outcomes |
| Modal/dialog | Focused confirmation failures |
| Global/system | Maintenance / session / platform notices |

---

## 9. Recovery Architecture

| Path | Use |
| --- | --- |
| Retry | When safe and server allows |
| Edit and resubmit | Validation failures |
| Refresh | Stale presentation |
| Re-authenticate | Session/security requirements ([`07`](07-security-and-session-management.md)) |
| Return | Back to prior safe context |
| Safe exit | Leave high-stakes flow without inventing success |
| Contact/support | Where product UX already provides |

---

## 10. Retry Rules

| May retry carefully | Do not blindly retry |
| --- | --- |
| Search/filter/pagination | Payments |
| Non-destructive reads | Exam submission |
| Safe bookmark/notification toggles after conflict refresh | Destructive actions |
| | Workflow transitions (approve/publish) |

Conceptual rule: retries must respect server idempotency and business outcomes. UI must not invent success after an uncertain request. Exact API idempotency is defined by future implementation under [`08`](08-api-design.md) / services—not here.

---

## 11. Authentication Recovery

Cover: expired session; invalid session; re-authentication; login redirect; intended destination where safe; password/security recovery.

Authority: [`07`](07-security-and-session-management.md). Browser state is not proof of authentication.

---

## 12. Authorization / Permission Recovery

Clear denial; no information leakage about protected resources; safe navigation; server authority for RBAC ([`03`](03-user-roles.md), [`09`](09-business-rules.md)).

---

## 13. Entitlement Recovery

Locked content; expired entitlement; pending payment; failed payment; upgrade path.

UI never implies Premium access without server entitlement state ([`09`](09-business-rules.md)).

---

## 14. Assessment Error / Recovery

Critical. Conceptual failure surfaces:

| Situation | Frontend role |
| --- | --- |
| Network interruption | Communicate uncertainty; re-sync from server |
| Answer persistence failure | Show failure; do not invent saved answers |
| Stale attempt | Present server conflict; follow attempt rules |
| Timer synchronization issue | Display server timer truth when available |
| Submission failure | No false “submitted/scored” |
| Duplicate submission | Present server outcome for Completed/InProgress rules |
| Session expiration | Re-auth path; fail closed |
| Unavailable question | Server message; safe next action |
| Browser refresh / accidental navigation | Re-establish from server attempt state |

**Authority:** [`07`](07-security-and-session-management.md), [`09`](09-business-rules.md) (attempt creation, InProgress resume, Completed no live resume, auto-submit on timeout, scoring via frozen question versions). This document does **not** invent recovery business rules.

---

## 15. Learning Error / Recovery

Lesson unavailable; progress update failure; completion update failure; media failure—communicate clearly; progress mutations remain server authoritative.

---

## 16. Library / Reader Recovery

Access denial; missing content; loading failure; bookmark failure; download failure. Storage URLs/keys are not authorization.

---

## 17. Subscription / Payment Recovery

Checkout failure; pending state; payment failure; uncertain payment result; retry/reconciliation path via server.

**Never** display payment success without server confirmation ([`09`](09-business-rules.md): entitlements activate only after verified payment or audited manual grant).

---

## 18. Staff / Admin Recovery

Permission denial; stale records; conflict; failed publish; failed approval; bulk operation failure. Workflow states remain those approved in [`09`](09-business-rules.md).

---

## 19. HTMX Error Boundary

Failed partial updates must not silently leave incorrect UI. Prefer explicit error fragment/state, refresh from server, or safe full navigation for high-stakes flows.

---

## 20. Alpine Error Boundary

Local UI failures degrade safely (close disclosure, restore focus). Alpine cannot decide business outcomes.

---

## 21. Accessibility Error Contract

Align with [`20`](20-frontend-accessibility-architecture.md): focus to errors; announcements; non-color status; keyboard recovery paths.

---

## 22. Localization Error Contract

Align with [`19`](19-frontend-form-validation-architecture.md)–[`20`](20-frontend-accessibility-architecture.md): localized messages; Bangla/English expansion; no English-width assumptions.

---

## 23. Responsive Error Presentation

Errors remain readable and actionable on mobile, tablet, and desktop; assessment recovery controls remain touch-usable.

---

## 24. Security-Aware Error Handling

Never expose: secrets; tokens; passwords; filesystem paths; internal stack traces; private payment information; protected content.

---

## 25. Error Data Contract

Conceptual fields for presentation only: user-safe message; severity; state; recovery action; accessibility metadata; localization information.

Do not define API schemas.

---

## 26. Error Logging / Observability Boundary

| Layer | Belongs |
| --- | --- |
| User presentation | Safe, localized messages |
| Server logs | Technical detail for operators |
| Monitoring | Aggregated failure signals |

Do not prescribe vendors. Do not send secrets to client logs.

---

## 27. Testing Strategy

Conceptual: validation; auth; session; entitlement; payment uncertain/fail; assessment submit fail; HTMX partial fail; Alpine degrade; a11y; i18n; no false success; regression.

---

## 28. Performance Considerations

Fail fast to clear state; avoid retry storms; align with [`21`](21-frontend-performance-architecture.md). Correctness over speed.

---

## 29. Governance

Ownership; security/UX/a11y review for new error patterns; no duplicate severity systems; deprecation of unsafe messages.

---

## 30. Future-only Extensions

**Future-only:** Offline Mode conflict UI; advanced real-time sync recovery; Institution Portal multi-tenant error surfaces; Flutter-specific recovery patterns.

---

## 31. Cross References

[`03`](03-user-roles.md), [`07`](07-security-and-session-management.md), [`09`](09-business-rules.md), [`11`](11-ui-ux-specification.md), [`13`](13-frontend-architecture.md)–[`21`](21-frontend-performance-architecture.md).

**This document does not modify any approved or draft predecessor.**

---

## 32. Acceptance Criteria

Accept when taxonomy, severity, lifecycle, presentation, recovery, retry safety, auth/authz/entitlement/assessment/learning/library/payment/staff recovery, HTMX/Alpine boundaries, a11y/i18n/security contracts, data/observability boundaries, testing, performance, governance, and Future-only extensions are defined; no implementation artifacts; docs `00`–`21` unchanged; locked precedence preserved.

---

## 33. Document Lock

**Status:** `docs/22-frontend-error-recovery-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend error and recovery architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`21` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

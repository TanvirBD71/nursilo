# Nursilo — Frontend Security Trust Boundary Architecture

| Field | Value |
| --- | --- |
| Document | `24-frontend-security-trust-boundary-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`23`](23-frontend-state-management-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual security trust boundary between browser/client, frontend presentation, application services, domain logic, and server-side security authority for Nursilo V1 |
| Out of scope | Exploit instructions; HTML/CSS/JS/Alpine/HTMX/Django/Python source; API/DB/infra implementation; framework-specific CSRF code; Figma |
| Nature | **Additive only** — does not modify locked docs `00`–`23`. Does not invent new RBAC, entitlement, payment, or assessment rules. |

---

## 1. Metadata

See table above. Nursilo includes authentication, student/staff accounts, subscriptions, payments, protected content, assessments, scoring, and sensitive account data—security responsibilities must not migrate into templates, CSS, Alpine, HTMX, or browser state.

---

## 2. Purpose

Define **where trust ends**. The frontend presents outcomes; the server validates, authorizes, and persists truth per [`07`](07-security-and-session-management.md) and [`09`](09-business-rules.md).

```text
User → Browser (untrusted)
    → Frontend presentation (untrusted for security decisions)
    → Request boundary
    → Application / service layer
    → Domain / security rules
    → Persistence / infrastructure
```

---

## 3. Relationship to docs/07, 09, 13–23

| Document | Role |
| --- | --- |
| [`03`](03-user-roles.md) | RBAC model |
| [`04`](04-system-architecture.md) | Layered architecture |
| [`05`](05-domain-model.md) | Domain aggregates |
| [`07`](07-security-and-session-management.md) | Auth/session/CSRF authority |
| [`08`](08-api-design.md) | Future API clients same services |
| [`09`](09-business-rules.md) | Entitlement/payment/assessment/workflow |
| [`13`](13-frontend-architecture.md)–[`18`](18-frontend-interaction-architecture.md) | Frontend stack boundaries |
| [`19`](19-frontend-form-validation-architecture.md)–[`23`](23-frontend-state-management-architecture.md) | Forms, a11y, performance, errors, state (drafts) |

---

## 4. Trust Boundary Principles

| Principle | Meaning |
| --- | --- |
| Browser is untrusted | Any client value can be forged |
| Frontend is not security boundary | UI cannot grant access |
| Server validates | Inputs re-checked server-side |
| Server authorizes | RBAC decisions server-side |
| Server owns entitlement | Free/Premium truth server-side |
| Server owns payment truth | Confirmation server-side |
| Server owns assessment truth | Attempt/timer/score server-side |
| Hidden UI is not protection | Omitting markup ≠ deny |
| Disabled UI is not protection | Disabled controls ≠ deny |
| Client validation is not security validation | Hints only |

---

## 5. Trust Boundary Model

| Boundary | Meaning |
| --- | --- |
| User | Human actor; may be hostile or mistaken |
| Browser | Fully attacker-controlled environment |
| Frontend presentation | Templates/HTMX/Alpine/CSS—display only |
| Request boundary | Authenticated requests + CSRF for state changes ([`07`](07-security-and-session-management.md)) |
| Application/service | Adapters invoke services; enforce authz |
| Domain/security rules | Business + security invariants |
| Persistence/infrastructure | Data at rest; secrets never to browser |

---

## 6. Authentication Boundary

Session state; login; logout; expiration; re-authentication; password/security flows—server owns validity. Max concurrent sessions and timeouts per [`07`](07-security-and-session-management.md). Browser cookies/storage are not proof without server validation.

---

## 7. Authorization / RBAC Boundary

Server owns: permission; role; capability; access decision ([`03`](03-user-roles.md)). Frontend only presents server-provided outcomes (hide/show is UX, not enforcement).

---

## 8. Entitlement Boundary

Server owns: Free/Premium access; subscription state; entitlement; expiration ([`09`](09-business-rules.md)). No optimistic Premium.

---

## 9. Payment Security Boundary

Server owns: payment confirmation; transaction truth; subscription activation; failure/pending state. Never trust browser payment success events as final truth. Capabilities activate only after verified payment or audited manual grant ([`09`](09-business-rules.md)).

---

## 10. Assessment Security Boundary

Server owns: attempt identity; question version; timer truth; answers; submission; scoring; completion ([`09`](09-business-rules.md)). Client may request transitions only.

---

## 11. Protected Content Boundary

| Not protection |
| --- |
| Hidden content in DOM |
| Disabled buttons |
| Frontend-only routes |
| Storage URLs/keys treated as automatic authorization |

Access checks occur server-side before content delivery.

---

## 12. Form Security Boundary

Align with [`19`](19-frontend-form-validation-architecture.md): server validation authoritative; sensitive fields never echoed; security-safe errors; duplicate submit guards are UX aids, not sole protection.

---

## 13. HTMX Security Boundary

HTMX is an enhancement layer, not authorization. State-changing HTMX follows the same CSRF and authz policy as ordinary authenticated mutations ([`07`](07-security-and-session-management.md)).

---

## 14. Alpine Security Boundary

Alpine is local UI behavior only. It must not store secrets as authority or grant access.

---

## 15. Template Security Boundary

Templates present prepared data. They do not calculate RBAC, entitlement, scores, or payment confirmation.

---

## 16. Styling Security Boundary

CSS never determines access. Visual “locked” styles are presentation of server state only ([`17`](17-frontend-styling-architecture.md)).

---

## 17. Client State Security Boundary

Browser state is untrusted ([`23`](23-frontend-state-management-architecture.md)). Tampered local state must fail closed on the server.

---

## 18. URL / Navigation Security

Navigation targets may be suggested by the UI; access is re-checked server-side on each request. Do not invent deep-link implementation here.

---

## 19. Error Security

Align with [`22`](22-frontend-error-recovery-architecture.md): no secrets, stack traces, paths, tokens, or protected content in user messages.

---

## 20. Logging / Sensitive Data Boundary

| Channel | Content |
| --- | --- |
| User-visible messages | Safe, localized |
| Application logs | Operational detail (server-side) |
| Audit logs | Security-relevant events per [`09`](09-business-rules.md) |
| Security monitoring | Aggregated signals |

Never expose secrets to client-side logs or UI.

---

## 21. CSRF / Request Integrity Boundary

Follow [`07`](07-security-and-session-management.md): CSRF required for cookie-authenticated state-changing requests; HTMX included. Do not generate framework-specific code here.

---

## 22. File Upload Security Boundary

Server validates files (type/size/policy). Frontend only presents selection/status/progress. Storage access remains server-mediated.

---

## 23. Session Security

Align with [`07`](07-security-and-session-management.md): opaque session ids; regeneration after auth; idle/absolute timeouts; revoke; concurrent session cap; device management without secret leakage.

---

## 24. Security-Sensitive Interaction Patterns

Require heightened care: password changes; re-auth; logout all; account security; payment; assessment submit; staff destructive actions—confirmation/re-auth as mandated by locked docs; no false success.

---

## 25. Security Failure / Recovery

Align with [`22`](22-frontend-error-recovery-architecture.md): fail closed; re-authenticate; safe exit; no information leakage.

---

## 26. Security + Accessibility

Security must not create inaccessible critical flows ([`20`](20-frontend-accessibility-architecture.md)). Captchas/challenges, if ever added, remain Future unless approved elsewhere.

---

## 27. Security + Localization

Security messaging must remain clear in Bangla and English without leaking internals.

---

## 28. Security + Performance

Never weaken security for performance ([`21`](21-frontend-performance-architecture.md)).

---

## 29. Threat-Aware Frontend Design

Conceptually design against (no exploit instructions): tampered browser state; modified requests; forged UI state; replay/duplicate actions; stale pages; unauthorized direct navigation; manipulated client values.

Controls: server re-validation; CSRF; authz on every request; idempotency/business rules server-side; fail closed.

---

## 30. Security Testing Strategy

Conceptual: authorization; session; entitlement; payment-state; assessment integrity; tampered-client-state; direct-navigation; sensitive-data exposure; CSRF on state-changing paths; regression.

---

## 31. Governance

Security review for new frontend surfaces touching auth, payment, assessment, or admin; no client authority creep; locked docs win.

---

## 32. Future-only Extensions

**Future-only:** MFA UX; advanced device attestation; Offline Mode security model; Flutter token model details; Institution Portal tenancy isolation UX.

Must not silently become V1 requirements unless already in locked docs.

---

## 33. Cross References

[`03`](03-user-roles.md), [`04`](04-system-architecture.md), [`05`](05-domain-model.md), [`07`](07-security-and-session-management.md), [`08`](08-api-design.md), [`09`](09-business-rules.md), [`13`](13-frontend-architecture.md)–[`23`](23-frontend-state-management-architecture.md).

**This document does not modify any approved or draft predecessor.**

---

## 34. Acceptance Criteria

Accept when trust principles/model, authn/authz/entitlement/payment/assessment/content/form/HTMX/Alpine/template/styling/client-state/URL/error/logging/CSRF/upload/session boundaries, sensitive interaction patterns, failure recovery, a11y/i18n/performance security intersections, threat-aware design (non-exploitative), testing, governance, and Future-only extensions are defined; no new business/RBAC/payment/scoring rules invented; no implementation artifacts; docs `00`–`23` unchanged by this creation.

---

## 35. Document Lock

**Status:** `docs/24-frontend-security-trust-boundary-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend security trust boundary architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`23` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

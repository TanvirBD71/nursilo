# Nursilo — Frontend Form & Validation Architecture

| Field | Value |
| --- | --- |
| Document | `19-frontend-form-validation-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`18`](18-frontend-interaction-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual frontend form and validation architecture for Nursilo V1 |
| Out of scope | HTML; CSS; Tailwind classes; JavaScript source; Alpine source; HTMX attributes; Django template source; Python; API implementation; serializers; database models; migrations; Figma; implementation configuration |
| Nature | **Additive only** — does not modify locked docs `00`–`18` |

---

## 1. Purpose

Nursilo needs a dedicated **form and validation architecture** so authentication, profile, assessment, billing, and staff forms share predictable structure, validation ownership, submission behavior, feedback, and recovery—without embedding business rules in the browser.

| Layer | Authority |
| --- | --- |
| [`12`](12-design-system.md)–[`17`](17-frontend-styling-architecture.md) | Visual / component / page / template / styling foundations |
| [`18`](18-frontend-interaction-architecture.md) | Interaction behavior |
| **This document** | Form composition, validation, submission, and recovery |
| Future implementation | Actual form templates / HTMX / Alpine wiring |

```text
12 → 13 → 14 → 15 → 16 → 17 → 18
    ↓
19 Form & Validation Architecture
    ↓
Future implementation
```

---

## 2. Form Architecture Principles

| Principle | Meaning |
| --- | --- |
| Server validation authority | Server decisions are definitive |
| Progressive enhancement | Forms work with ordinary submission |
| Accessibility | Labels, errors, focus, announcements |
| Localization | Bangla / English / mixed-language safe |
| Reuse | Shared field and form patterns |
| Security | Sensitive forms follow [`07`](07-security-and-session-management.md) |
| Predictable states | Explicit idle → editing → submitting → result |
| Graceful failure | Clear, recoverable errors |
| Duplicate submission prevention | Especially payments, exam submit, destructive actions |
| No business logic in forms | No scoring, entitlement, RBAC, or payment truth in the client |

---

## 3. Form Hierarchy

```text
Form
→ Form Section
→ Field Group
→ Field
→ Input Control
→ Feedback
```

| Level | Responsibility |
| --- | --- |
| **Form** | One primary purpose; submission boundary |
| **Section** | Related field groups |
| **Field group** | Closely related fields (e.g., name parts) |
| **Field** | Label + control + help + error |
| **Input control** | Concrete control type |
| **Feedback** | Validation / status messaging |

---

## 4. Form Taxonomy

| Family | Examples / notes |
| --- | --- |
| Authentication | Register, login, verify, reset |
| Profile | Personal / academic profile |
| Security | Password change, re-auth, devices |
| Search | Course, library, staff search |
| Filter | Catalog / queue filters |
| Learning | Goals, preferences where applicable |
| Assessment setup | Scope, filters, start confirmation |
| Assessment submission controls | Answer persistence, submit, confirm |
| Library | Bookmark, download request presentation |
| Subscription | Plan, checkout-related fields |
| Staff / admin | CRUD, queues, bulk actions |
| CMS / editorial | Draft metadata, publish confirmations |
| Upload | Content / media selection feedback |

---

## 5. Field Architecture

| Element | Role |
| --- | --- |
| Label | Accessible name; always associated |
| Input | Control receiving value |
| Help text | Non-error guidance |
| Validation message | Localized, field-associated error |
| Required / optional | Server-defined; clearly indicated |
| Disabled / readonly | Presentation of server/policy state |
| Sensitive field handling | Passwords and secrets never echoed back |

---

## 6. Validation Architecture

| Layer | Authority |
| --- | --- |
| Server validation | Authoritative |
| Client hints | Optional UX only; never sole gate |
| Field validation | Per-field messages |
| Form-level validation | Cross-field / form summary |
| Summary errors | Page/form top where appropriate |
| Localized errors | Bangla / English |
| Business conflicts | From [`09`](09-business-rules.md) via server |
| Security-safe errors | No enumeration leakage; no secrets |

---

## 7. Form State Model

Conceptual states: initial; editing; dirty; submitting; loading; success; validation error; server error; business conflict; permission denied; session expired; cancelled; retryable; non-retryable.

State must never imply persistence or success the server has not confirmed.

---

## 8. Submission Architecture

| Concern | Rule |
| --- | --- |
| Ordinary submission | Full form post remains valid baseline |
| Enhanced submission | HTMX may enhance where appropriate |
| Duplicate prevention | Disable/guard while submitting; server idempotency where required |
| Loading | Understandable; not indefinite |
| Server response | Authoritative result |
| Redirect | Preferred after major auth/security/payment successes |
| Partial update | For small inline forms when safe |
| Recovery | Clear retry or safe exit |

---

## 9. HTMX Form Boundary

| Allowed | Forbidden |
| --- | --- |
| Inline validation presentation | Authorization |
| Partial form updates | Entitlement |
| Modal forms | Scoring |
| Search/filter forms | Payment confirmation |
| Staff inline updates | Workflow authority |

---

## 10. Alpine Form Boundary

| Allowed | Forbidden |
| --- | --- |
| Password visibility | Server validation authority |
| Local field interaction | Permissions / entitlement |
| Disclosure | Payment truth |
| Temporary UI state | Persistence authority |

---

## 11. Security-Sensitive Forms

Cover: password change; password reset; re-authentication; email verification; device management; logout all; payment-related forms.

Follow [`07`](07-security-and-session-management.md): re-auth where required; security-safe messaging; no secret leakage; server owns session outcomes.

---

## 12. Assessment Forms / Controls

| Server owns |
| --- |
| Attempt; answers; submission; scoring; timer; completion |

Client presents controls and requests transitions only. Align with [`18`](18-frontend-interaction-architecture.md) assessment rules.

---

## 13. File Upload Architecture

Conceptual: file selection; validation feedback; upload progress presentation; failure; retry; access/security expectations.

Do not define storage implementation. Storage URLs/keys are never authorization.

---

## 14. Error Presentation

| Placement | Use |
| --- | --- |
| Inline | Field-associated validation |
| Summary | Multiple form errors |
| Page-level | Workflow / auth / payment outcomes |
| Server error | Non-sensitive recovery messaging |

Security-safe messaging always.

---

## 15. Accessibility Contract

Labels; focus management; keyboard access; error association; screen-reader-compatible naming; status announcements for submit/result.

Align with upcoming [`20`](20-frontend-accessibility-architecture.md) and existing docs/11–18.

---

## 16. Localization Contract

Support Bangla; English; mixed language; long labels; localized dates/numbers/currency; medical terminology; localized validation messages.

---

## 17. Responsive Form Architecture

| Viewport | Behavior |
| --- | --- |
| Mobile | Single-column; large targets; completable checkout/auth |
| Tablet | Comfortable spacing; readable fields |
| Desktop | Wider where justified; staff denser layouts |

---

## 18. Form Data Contract

Forms receive server-provided display state only: labels; values; options; errors; actions/URLs; permission/entitlement presentation; localized messages.

Forms must not query repositories or calculate business outcomes.

---

## 19. Form Composition Rules

1. One primary purpose per form.  
2. Reuse field/components before inventing new ones.  
3. Keep page workflows out of shared field components where possible.  
4. Keep business rules outside forms.  
5. Prefer clear sections over giant flat forms.  
6. Preserve accessibility and localization.  

---

## 20. Naming Conventions

| Good | Avoid |
| --- | --- |
| LoginForm, ChangePasswordForm, PracticeSetupForm, ExamSubmitControl, ContentApprovalForm | Form2, BigForm, TempFields, FinalFinalForm |

---

## 21. Reuse Rules

Search existing form/field vocabulary; reuse when semantics match; extend only if coherent; create new only when reuse harms clarity.

---

## 22. Security-Aware Form Rules

Never expose passwords, tokens, session identifiers, secrets, private payment data, or protected content. Client-only checks are not a security boundary.

---

## 23. Testing Strategy

Conceptual: field association; validation presentation; submit/loading/success/error; duplicate submit guard; accessibility; localization; HTMX/Alpine boundaries; security forms; assessment controls; regression.

Does not replace domain/service validation tests.

---

## 24. Performance Guidance

Avoid unnecessary requests; keep assessment controls lightweight; prefer partial updates only when beneficial; do not trade correctness for speed.

---

## 25. Governance

Ownership; UX/security/accessibility review; duplicate prevention; breaking changes; deprecation. New form families require justification.

---

## 26. Future-only Extensions

**Future-only:** advanced adaptive forms; Offline Mode form sync; AI-assisted form fill; Flutter form equivalents; Institution Portal forms.

Must not silently become V1 requirements.

---

## 27. Cross References

| Document | Use |
| --- | --- |
| [`07`](07-security-and-session-management.md) | Sensitive forms |
| [`09`](09-business-rules.md) | Business conflicts |
| [`11`](11-ui-ux-specification.md)–[`18`](18-frontend-interaction-architecture.md) | UX through interaction foundations |

**This document does not modify any approved document.**

---

## 28. Acceptance Criteria

Accept when: principles, hierarchy, taxonomy, fields, validation, states, submission, HTMX/Alpine boundaries, security-sensitive and assessment forms, uploads, error presentation, a11y/i18n/responsive contracts, data contract, composition/naming/reuse/security rules, testing, performance, governance, and Future-only extensions are defined; **no** implementation source generated; docs `00`–`18` unchanged.

---

## 29. Document Lock

**Status:** `docs/19-frontend-form-validation-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend form and validation architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`18` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

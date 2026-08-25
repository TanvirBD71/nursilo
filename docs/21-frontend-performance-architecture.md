# Nursilo — Frontend Performance Architecture

| Field | Value |
| --- | --- |
| Document | `21-frontend-performance-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`20`](20-frontend-accessibility-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual frontend performance architecture for Nursilo V1 |
| Out of scope | Actual performance code; CSS; Tailwind config; JavaScript; Django templates; Python; API implementation; database implementation; CDN configuration; server infrastructure; vendor-specific configuration; hard numeric performance budgets unless already established by locked docs |
| Nature | **Additive only** — does not modify locked docs `00`–`20` |

---

## 1. Purpose

Nursilo needs a **frontend performance architecture** so learner, assessment, reader, public, and staff surfaces remain responsive without premature optimization, SPA complexity, or sacrificing correctness, accessibility, or security.

```text
13 Frontend Architecture → 18 Interaction → 19 Forms → 20 Accessibility
    ↓
21 Performance Architecture
    ↓
Future implementation
```

This document defines strategy and boundaries. It does **not** lock tooling vendors or numeric budgets not already in locked docs.

---

## 2. Performance Principles

| Principle | Meaning |
| --- | --- |
| Correctness first | Right results before faster wrong results |
| Server-rendered first paint | HTML first for critical content |
| Minimal JavaScript | Enhance; do not rebuild the app in JS |
| Progressive enhancement | Core flows without heavy client logic |
| Avoid premature optimization | Measure and prioritize real bottlenecks later |
| Mobile-first | Learner phones matter |
| Accessibility preserved | Speed never strips semantics/focus |
| Security preserved | Never trade security for latency |

---

## 3. Performance Ownership Model

| Layer | Responsibility |
| --- | --- |
| Backend / service | Efficient authorized data preparation |
| Presentation boundary | Lean view models; no N+1 presentation anti-patterns conceptually |
| Templates | Avoid excessive nesting/duplication |
| Components | Reuse; avoid giant trees |
| Styling | Prefer token/utility discipline ([`17`](17-frontend-styling-architecture.md)) |
| Interactions | Minimize unnecessary requests ([`18`](18-frontend-interaction-architecture.md)) |
| Assets | Right-sized media; lazy where appropriate |

---

## 4. Rendering Performance

| Concern | Guidance |
| --- | --- |
| Server-rendered HTML | Primary delivery model |
| First paint | Prioritize critical content |
| Critical content | Above-the-fold purpose of the page |
| Partial updates | Smaller fragments when beneficial |
| DOM complexity | Avoid unnecessary depth and duplication |

---

## 5. JavaScript Performance

| Concern | Guidance |
| --- | --- |
| Minimal JS | Default |
| Alpine scope | Local UI only |
| No SPA | Not V1 direction ([`13`](13-frontend-architecture.md)) |
| Avoid unnecessary execution | No idle heavy work |
| Avoid excessive event handling | Prefer simple, bounded listeners conceptually |

---

## 6. HTMX Performance

| Concern | Guidance |
| --- | --- |
| Partial updates | Prefer over full reload when appropriate |
| Request minimization | Do not refresh unrelated regions |
| Fragment size | Keep responses focused |
| Avoid unnecessary refreshes | Especially assessment |
| Loading states | Clear; not indefinite ([`18`](18-frontend-interaction-architecture.md)) |

---

## 7. Asset Performance

| Asset | Guidance |
| --- | --- |
| Images / icons / fonts | Optimize conceptually; avoid oversized delivery |
| CSS / JS | Minimal necessary payloads |
| Lazy loading | Non-critical media where appropriate |
| Responsive media | Serve suitable sizes conceptually |

---

## 8. Learning Performance

Lesson rendering; progress updates; navigation; media—keep reading smooth; avoid heavy chrome; progress updates must remain server-authoritative without chatty waste.

---

## 9. Assessment Performance

Critical:

| Requirement |
| --- |
| Lightweight exam UI |
| Low interaction latency for answer/navigation |
| Timer display without heavy decoration |
| Question navigation remains snappy |
| Minimal unnecessary requests |
| Stable layout |
| Reliable submission UX |

Correctness of attempt/timer/submission outranks cosmetic speed.

---

## 10. Library / Reader Performance

Reading content primary; book covers/media restrained; reader width stable; navigation light.

---

## 11. Staff / Admin Performance

Large tables via pagination; efficient filters; queue refresh discipline; careful bulk operations—density without loading entire datasets at once.

---

## 12. Public / SEO Performance

Server rendering; crawlable public content; restrained media; minimal JS on marketing pages.

---

## 13. Caching Boundaries

Conceptual only: public/cacheable content may benefit from caching strategies later; private learner/staff/assessment content must not be cached unsafely.

Do not prescribe infrastructure, CDN, or cache products here.

---

## 14. Network Efficiency

Request minimization; partial responses; duplicate request avoidance; disciplined retries—never retry payment confirmation or exam submit blindly in ways that invent success.

---

## 15. Loading States

Align with [`18`](18-frontend-interaction-architecture.md): understandable loading; layout stability where practical; never hide errors behind infinite spinners.

---

## 16. Error / Recovery Performance

Failures should fail fast to a clear state; recovery actions should not spawn request storms.

---

## 17. Localization Performance

Bangla/English assets and text expansion must not cause layout collapse or interaction failure. Do not assume English widths.

---

## 18. Accessibility Performance

Performance optimization must **not** remove semantic structure, focus management, or accessible names/announcements ([`20`](20-frontend-accessibility-architecture.md)).

---

## 19. Security Performance Boundary

Never sacrifice CSRF, auth checks, entitlement checks, or safe rendering for speed. Hidden/disabled UI is not a security optimization.

---

## 20. Measurement & Observability

Conceptual metrics (no vendor lock): page responsiveness; interaction latency; error rate; failed requests; frontend exceptions; assessment submission failures.

Exact tooling is Future/implementation concern.

---

## 21. Performance Testing

Conceptual: page performance; mobile; assessment; reader; staff/admin; regression against performance anti-patterns.

---

## 22. Performance Anti-Patterns

| Avoid |
| --- |
| Unnecessary SPA |
| Excessive JavaScript |
| Giant DOM trees |
| Repeated/chatty requests |
| Oversized media |
| Excessive animations |
| Duplicate components/markup |
| Client-side business logic “for speed” |

---

## 23. Performance Governance

Ownership; review for high-risk surfaces (assessment, payment, public); prevent premature complexity; document exceptions.

---

## 24. Future-only Extensions

**Future-only:** Offline Mode performance; advanced CDN/edge strategies; Flutter client performance budgets; AI Tutor streaming UX; Adaptive Learning heavy analytics UIs; Real-time collaboration.

Must not silently become V1 requirements.

---

## 25. Cross References

| Document | Use |
| --- | --- |
| [`13`](13-frontend-architecture.md) | Server-rendered / HTMX / Alpine direction |
| [`15`](15-frontend-page-architecture.md)–[`18`](18-frontend-interaction-architecture.md) | Page/interaction performance expectations |
| [`19`](19-frontend-form-validation-architecture.md) | Form submission efficiency (draft) |
| [`20`](20-frontend-accessibility-architecture.md) | A11y must not be sacrificed (draft) |
| [`07`](07-security-and-session-management.md) / [`09`](09-business-rules.md) | Security & business truth constraints |

**This document does not modify any approved document.**

---

## 26. Acceptance Criteria

Accept when: principles, ownership, rendering/JS/HTMX/asset guidance, learning/assessment/library/staff/public performance rules, caching boundaries (conceptual), network efficiency, loading/error/localization/a11y/security boundaries, measurement, testing, anti-patterns, governance, and Future-only extensions are defined; **no** implementation/infra config generated; **no** unjustified numeric budgets invented; docs `00`–`20` not modified by this document.

---

## 27. Document Lock

**Status:** `docs/21-frontend-performance-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend performance architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`20` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

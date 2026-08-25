# Nursilo — Frontend Architecture

| Field | Value |
| --- | --- |
| Document | `13-frontend-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`12`](12-design-system.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative frontend architecture and implementation-boundary specification for Nursilo V1 |
| Out of scope | Application source code; actual templates; CSS; JavaScript; API endpoint definitions; database schemas; migrations |
| Nature | **Additive only** — does not modify locked docs `00`–`12` |

---

## 1. Purpose

This document defines how the Nursilo **frontend is organized**, which technology owns which responsibility, and how the presentation layer stays a thin adapter over domain services.

| Clarification | Rule |
| --- | --- |
| Frontend role | **Adapter** — renders and enhances experience |
| Business logic | Remains in **application/domain services** |
| UI authority | Experience follows [`11`](11-ui-ux-specification.md); visuals follow [`12`](12-design-system.md) |
| Security / rules | Follow [`07`](07-security-and-session-management.md), [`09`](09-business-rules.md) |

The frontend must **not** become a second business-logic layer. Backend services remain authoritative for entitlements, RBAC, scoring, payments, sessions, and editorial state.

This is an **architecture specification**, not implementation. No application source code is generated here.

---

## 2. Frontend Architecture Principles

| Principle | Meaning |
| --- | --- |
| **Server truth** | Attempt state, timers, scores, entitlements, and sessions are decided server-side |
| **Progressive enhancement** | Usable HTML first; HTMX/Alpine enhance |
| **Service-layer authority** | Presentation calls services; never repositories |
| **Minimal client state** | Browser holds temporary UI state only |
| **Security by default** | CSRF, XSS-safe rendering, no secret exposure |
| **Accessibility by default** | Semantic structure and keyboard paths from the start |
| **Mobile-first** | Learner flows designed for phones first |
| **Reusability** | Shared layouts/partials/components |
| **Consistency with docs/11 and docs/12** | No rogue UX or visual patterns |
| **Performance** | Minimal JS; efficient partial updates |
| **Graceful degradation** | Core flows work if enhancement fails |
| **Explicit state transitions** | Loading/empty/error/success are first-class |
| **No duplicated business rules** | Do not re-implement scoring/RBAC/entitlements in JS |
| **No client-side entitlement authority** | UI may display Free/Premium; never decide it |

---

## 3. Technology Direction

Approved conceptual V1 frontend stack:

| Layer | Technology |
| --- | --- |
| Primary rendering | **Django Templates** |
| Partial enhancement | **HTMX** |
| Lightweight UI state | **Alpine.js** |
| Styling | **Tailwind CSS** mapped to the approved design system |
| Server | **Django** |
| Future clients | REST/API adapter for Flutter and others ([`08`](08-api-design.md)) |

**Why this stack fits Nursilo V1**

- Strong SEO for public/CMS content  
- Fast delivery of educational HTML without SPA complexity  
- HTMX covers filters, pagination, and inline updates without a heavy client framework  
- Alpine covers small interactive affordances  
- Same Django services power Templates now and API/Flutter later  

Package versions and config files are out of scope.

---

## 4. Frontend Layer Model

```text
Browser
  ↓
Django Template / HTML presentation
  ↓
HTMX / Alpine enhancement
  ↓
Django presentation boundary (views as adapters)
  ↓
Application / domain services
  ↓
Repositories
  ↓
Persistence
```

| Forbidden | Reason |
| --- | --- |
| Templates calling repositories | Breaks architecture dependency rule |
| HTMX bypassing services | Creates insecure shortcuts |
| Alpine implementing authorization | Client is not trusted |
| JavaScript as source of truth | Violates server truth |

---

## 5. Server-Rendered First Strategy

| Prefer server-rendered HTML for | SEO/public content; learning pages; library pages; admin lists; forms; assessment results; authentication |
| --- | --- |

| Enhancement may be used for | Filters; inline updates; modal content; search interactions; notification read state; bookmark toggles; progressive sections |
| --- | --- |

| Prefer full navigation when | Crossing major IA boundaries; completing auth; starting/ending exams where a clean focus layout is clearer |
| --- | --- |

| Alpine appropriate when | Purely visual/local UI state (dropdowns, tabs, visibility) |
| --- | --- |

| JavaScript unnecessary when | Static content and ordinary form posts suffice |
| --- | --- |

---

## 6. HTMX Architecture

### Allowed

Partial page updates; server-rendered fragments; filtering; search; pagination; inline state changes; modal loading; form submission enhancement; notification updates; bookmark interactions.

### Not allowed

Business-rule decisions; authorization; entitlement decisions; scoring authority; payment authority; session authority; direct repository access.

**Server remains authoritative** for every HTMX response outcome.

---

## 7. Alpine.js Architecture

Lightweight UI-state enhancement only.

### Allowed

Dropdowns; tabs; disclosure; modal visibility; client visual state; countdown **display** (server time authoritative); password visibility toggle; temporary form interaction; UI preferences that do not change security posture.

### Not allowed

RBAC decisions; entitlement decisions; payment confirmation; exam scoring; exam submission authority; session validation; security authorization; persistent business state authority.

---

## 8. JavaScript Policy

| Rule |
| --- |
| JavaScript should be minimal |
| Prefer HTML/server behavior |
| No unnecessary SPA architecture |
| No client-side duplicate business logic |
| No sensitive state in `localStorage` unless explicitly approved later |
| No secrets in JavaScript |
| No trust in browser state for security |

JavaScript is an enhancement layer, not the application authority.

---

## 9. Template Architecture

Conceptual layout families:

| Layout | Use |
| --- | --- |
| Base | Shared shell |
| Public | Marketing/CMS |
| Auth | Login/register/reset |
| Student | Learner portal |
| Staff/admin | RBAC-scoped tools |
| Assessment focus | Live practice/exam chrome reduction |
| Reader | Book reading immersion |
| Error/system | 404/403/500/maintenance |

Define conceptually: layout inheritance; reusable partials; component fragments; page-specific composition; HTMX partial boundaries (fragments that can be swapped safely).

Do not create actual template files in this document.

---

## 10. Component Architecture

Conceptual reusable components (aligned with [`12`](12-design-system.md)):

Header, Footer, Navigation, Sidebar, Breadcrumb, Button, Form field, Alert, Modal, Dropdown, Badge, Card, Table, Pagination, Search, Notification, Progress, Empty state, Error state, Loading state, Question option, Exam timer, Question navigator, Book card, Course card.

Avoid duplication; compose from the design system vocabulary.

---

## 11. Page Composition

```text
Page → Layout → Section → Component → Data/state
```

Pages compose reusable patterns rather than one-off markup.

Page families: Public, Authentication, Student, Assessment, Library, Subscription, Staff, Admin, Error/system.

---

## 12. State Ownership

| State category | Owner |
| --- | --- |
| Server / domain state | Services + persistence |
| Session / authentication | Server session system |
| Authorization / entitlement | AccessControl + Entitlement services |
| Form submitted values | Server validation authoritative; client hints optional |
| UI state (open/closed) | Browser / Alpine (temporary) |
| Temporary interaction | Browser |
| Assessment runtime | Server (attempt, timer, score); client displays |

**Critical rule:** Server owns business truth. Browser owns only temporary presentation state.

---

## 13. Authentication Frontend Boundary

Align with [`07`](07-security-and-session-management.md).

Frontend supports UX for login, logout variants, session expiry, password reset, email verification, password change, device management, and re-authentication challenges.

Never treat browser state as proof of authentication. Expired sessions always require re-auth.

---

## 14. Authorization Frontend Boundary

Align with [`03`](03-user-roles.md), [`07`](07-security-and-session-management.md), [`09`](09-business-rules.md).

| Rule |
| --- |
| UI may hide unavailable actions |
| Hiding is **not** authorization |
| Server enforces every permission |
| Role visibility follows RBAC |
| Entitlement visibility follows EntitlementService |
| Forbidden states handled gracefully without leakage |

Never implement security solely in templates or JavaScript.

---

## 15. Free / Premium Frontend Architecture

Presentation may show: Free, Premium, Locked, Pending, Expired, Upgrade-required.

Frontend **displays** entitlement state supplied by the server. It must **never decide** entitlement state.

Premium UX follows [`11`](11-ui-ux-specification.md) and [`12`](12-design-system.md)—honest, non-manipulative.

---

## 16. Assessment Frontend Architecture

Supports: practice/exam setup and sessions; question navigation; timer display; answer selection; flagging; submit confirmation; auto-submit UX; results; review.

| Server authoritative for | Attempt state; timer; submission; scoring; completion; question version |
| --- | --- |

Client timer is display assistance only. No client-side scoring or submission authority.

---

## 17. Learning Frontend Architecture

Course navigation, lesson rendering, progress display, Continue Learning, completion cues, topic navigation, learning materials.

Progress mutations go through services—not client-only flags.

---

## 18. Library Frontend Architecture

Catalog, book detail, reader, download affordances, bookmarks, premium access messaging.

File access remains entitlement-aware. Storage URLs/keys are not authorization mechanisms.

---

## 19. Form Architecture

Server validation authoritative; client hints allowed; inline errors and summaries; success states; sensitive fields; re-authentication gates; file uploads; HTMX-enhanced forms where appropriate.

---

## 20. Search Architecture

Search input, grouped results, filters, pagination, empty/loading states, entitlement-aware result presentation.

Unpublished content must never leak through frontend rendering.

---

## 21. Notification Architecture

Indicator, list, read/unread, announcements, security notifications, priority presentation.

Frontend must not expose secrets.

---

## 22. Responsive Implementation Strategy

Mobile-first learner flows; tablet comfort; desktop admin density; exam focus mode; library reader immersion—aligned with docs `11` and `12`.

---

## 23. Accessibility Implementation Boundary

Frontend responsibilities (conceptual): semantic HTML structure; keyboard navigation; focus management; screen-reader-friendly naming; labels; ARIA only where needed; contrast mapping to design system; error identification; reduced motion; touch targets; zoom/text resizing support.

No actual HTML in this document.

---

## 24. Localization Implementation Strategy

Bangla and English; translation ownership for template/UI strings; localized errors; date/number/currency formatting; mixed-language content; long-string handling.

No hard-coded user-facing strings where localization requires translation. Exact Django translation APIs are not prescribed here.

---

## 25. Design System Implementation Boundary

| Design system concept | Later maps to |
| --- | --- |
| Design tokens | CSS/Tailwind implementation |
| Design components | Template / HTMX / Alpine components |
| Design states | Frontend state representations |

Not implemented in this document.

---

## 26. Asset Architecture

Conceptual handling of logos, icons, illustrations, course images, book covers, CMS media, question images, and static assets.

| Separate | Static application assets | vs | User-uploaded media |
| --- | --- | --- | --- |

Storage schema is out of scope (see [`06`](06-database-design.md) / architecture media rules).

---

## 27. Performance Architecture

Server-rendered first paint; minimal JavaScript; lazy loading where appropriate; image/asset optimization; partial updates; pagination; avoid over-fetching and unnecessary DOM complexity; skeleton states; cache-aware public pages.

Correctness and security take priority over optimization.

---

## 28. Security Architecture

Align with [`07`](07-security-and-session-management.md) and [`08`](08-api-design.md).

Frontend supports HTTPS, secure cookies, CSRF, session expiration UX, re-authentication, CSP-compatible architecture, XSS-safe rendering, no secret/token leakage, no unsafe HTML injection, and server authorization.

Never rely on client-side restrictions for security.

---

## 29. Error Handling Architecture

Validation, authentication, authorization, entitlement, business conflicts, 404, 500, maintenance, offline/best-effort, session expiration.

Errors remain localized and non-sensitive.

---

## 30. API Adapter Boundary

```text
Templates / HTMX  →  Django presentation adapter  →  Services
Flutter           →  API adapter                  →  Same services
```

Frontend architecture must not create a second business model.

---

## 31. Frontend Directory Organization

Conceptual areas only (no files created):

| Area | Ownership / boundary |
| --- | --- |
| `templates/` | Page templates and composition |
| `layouts/` | Base/public/auth/student/staff/exam/reader/error |
| `components/` / `partials/` | Reusable fragments and HTMX targets |
| `pages/` | Page-level templates by family (optional grouping) |
| `static/` | Application static assets |
| `styles/` | Design-system → Tailwind/CSS mapping (later) |
| `scripts/` | Minimal JS / Alpine entrypoints |
| `assets/` | Brand/media static packages as needed |
| `localization/` | Locale message catalogs (conceptual) |

Boundaries prevent dumping business logic into templates or scripts.

---

## 32. Testing Architecture

Conceptual categories: template rendering; accessibility; interaction; form validation; HTMX; Alpine; responsive; assessment UX; authentication UX; entitlement UI; regression; browser compatibility.

Business-rule correctness remains covered primarily by service/domain tests.

---

## 33. Observability

Principles: error reporting; failed interaction visibility; performance metrics; authentication failures; payment UI failures; assessment submission failures; client errors.

Never log passwords, tokens, session identifiers, sensitive payment information, or private learner content unnecessarily.

---

## 34. Deployment Boundary

Conceptual separation: source → static assets → user media → CDN/edge → Django application → browser.

Align with [`04`](04-system-architecture.md). No deployment scripts here.

---

## 35. Future Frontend Clients

Future: Flutter, Desktop, AI Tutor, Institution Portal, Offline Mode.

All reuse domain/business rules. Flutter is not a reason to duplicate business logic.

---

## 36. Frontend Architecture Governance

Architecture, component, accessibility, security, and performance reviews; controlled breaking changes; technical debt management; deprecation of frontend patterns.

No architectural change should silently violate docs `00`–`12`.

---

## 37. Cross References

| Document | Use |
| --- | --- |
| [`00`](00-project-vision.md)–[`02`](02-feature-list.md) | Product scope |
| [`03`](03-user-roles.md) | RBAC visibility |
| [`04`](04-system-architecture.md) | Adapter → service dependency |
| [`07`](07-security-and-session-management.md) | Auth/session UX boundaries |
| [`08`](08-api-design.md) | Future API clients |
| [`09`](09-business-rules.md) | Behavioral truth |
| [`10`](10-development-roadmap.md) | Delivery sequencing |
| [`11`](11-ui-ux-specification.md) | Experience |
| [`12`](12-design-system.md) | Visual system |

**This document does not modify any approved document.**

---

## 38. Acceptance Criteria

This document is acceptable when:

1. Frontend architecture is clearly defined  
2. Django Templates are the V1 primary rendering layer  
3. HTMX, Alpine.js, and JavaScript boundaries are defined  
4. Server-side business authority is preserved  
5. Template, component, and page composition are defined conceptually  
6. State ownership is defined  
7. Authentication, authorization, and Free/Premium frontend handling are defined  
8. Assessment, learning, library, form, search, and notification architectures are defined  
9. Responsive, accessibility, localization, and design-system implementation boundaries are defined  
10. Asset, performance, security, and error-handling architectures are defined  
11. Future API adapter boundary and future clients are addressed  
12. Conceptual directory organization, testing, observability, deployment boundary, and governance are defined  
13. **No** actual source code, API endpoint catalog, or database/schema artifacts are generated  
14. Docs `00`–`12` remain unmodified  

---

## 39. Document Lock

**Status:** `docs/13-frontend-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative frontend architecture and implementation-boundary specification for Nursilo V1. Substantive content remains unchanged. Docs `00`–`12` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

# Nursilo — Frontend Accessibility Architecture

| Field | Value |
| --- | --- |
| Document | `20-frontend-accessibility-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`19`](19-frontend-form-validation-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual frontend accessibility architecture for Nursilo V1 — system-wide accessibility contract |
| Out of scope | HTML; CSS; Tailwind; JavaScript; Alpine source; HTMX attributes; Django template source; Python; API/database implementation; Figma; implementation artifacts |
| Nature | **Additive only** — does not modify locked docs `00`–`19` |

---

## 1. Purpose

Nursilo requires a dedicated **accessibility architecture** so accessibility is not an afterthought bolted onto components. This document goes deeper than [`11`](11-ui-ux-specification.md) and docs/14–18 by defining accessibility as a **system-wide implementation contract** across design, components, pages, templates, interactions, and the presentation boundary.

```text
11 UX → 12 Design → 13–18 Frontend layers → 19 Forms (draft)
    ↓
20 Accessibility Architecture
    ↓
Future implementation
```

---

## 2. Accessibility Principles

| Principle | Meaning |
| --- | --- |
| Accessibility by default | Built into every surface family |
| Semantic structure | Meaning before visuals |
| Keyboard-first | All critical actions reachable without pointer |
| Screen-reader compatibility | Names, roles, states communicable |
| Visible focus | Never remove without equivalent |
| Non-color communication | Status with icon and/or text |
| Responsive accessibility | Works across viewports |
| Localization | Bangla/English/mixed content safe |
| Reduced motion | Honor user preference |
| Graceful degradation | Enhancement must not break base access |

---

## 3. Accessibility Ownership Model

| Layer | Responsibility |
| --- | --- |
| Design system ([`12`](12-design-system.md)) | Contrast intent, focus, status language |
| Components ([`14`](14-frontend-component-architecture.md)) | Accessible names, states, variants |
| Pages ([`15`](15-frontend-page-architecture.md)) | Heading hierarchy, landmarks, page title |
| Templates ([`16`](16-frontend-template-architecture.md)) | Semantic document structure |
| Styling ([`17`](17-frontend-styling-architecture.md)) | Focus/contrast presentation |
| Interactions ([`18`](18-frontend-interaction-architecture.md)) | Focus moves, announcements, recovery |
| Forms ([`19`](19-frontend-form-validation-architecture.md)) | Labels, error association |
| Server / presentation boundary | Provide correct state; never rely on client-only access |

---

## 4. Semantic Structure

Conceptual requirements (no HTML):

| Structure | Expectation |
| --- | --- |
| Landmarks | Main, navigation, complementary where justified |
| Headings | One clear hierarchy per page |
| Regions | Group related content |
| Lists | True lists for list content |
| Tables | Tabular data with headers |
| Forms | Proper field associations |
| Links vs buttons | Navigation vs actions distinguished |

---

## 5. Accessible Naming Architecture

| Control | Naming rule |
| --- | --- |
| Buttons / links | Purpose-clear names |
| Icons | Accessible name or adjacent text |
| Form fields | Persistent associated labels |
| Navigation | Distinct item names |
| Dialogs | Accessible title |
| Status indicators | Text/icon + not color alone |

---

## 6. Keyboard Interaction Architecture

Cover: tab order; keyboard reachability; activation; escape where appropriate; focus movement; focus restoration after dismiss/update.

---

## 7. Focus Management

| Situation | Expectation |
| --- | --- |
| Page transitions | Focus to meaningful start (e.g., main) |
| Modal open/close | Enter dialog; restore trigger |
| Partial updates | Preserve or move focus intentionally |
| Form errors | Move to summary or first error as appropriate |
| Assessment navigation | Predictable question/option focus |

---

## 8. Screen Reader Architecture

Announce conceptually: state changes; loading; success; error; validation; timer (carefully); assessment progress; notification updates—without flooding or leaking secrets.

---

## 9. Forms Accessibility

Align with [`19`](19-frontend-form-validation-architecture.md): labels; help text; error association; submit status; keyboard completion; sensitive fields not echoed.

---

## 10. Navigation Accessibility

Header; menus; breadcrumbs; tabs; pagination; mobile navigation—all keyboard reachable, named, and focus-visible.

---

## 11. Modal / Dialog Accessibility

Accessible title; focus trap while open; Escape where appropriate; restore focus; no critical content only in tooltips/popovers.

---

## 12. Assessment Accessibility

Special attention: question navigation; answer options; timer communication; flags; submission; results; correct/incorrect feedback with non-color cues. Server remains authority for attempt truth.

---

## 13. Learning Accessibility

Lessons; reading measure; progress presentation; hierarchy; materials—clear headings and operable controls.

---

## 14. Library / Reader Accessibility

Catalog controls; reader chrome; bookmark/actions; entitlement messaging—readable and keyboard operable; content primary in reader mode.

---

## 15. Staff / Admin Accessibility

Tables; filters; dense interfaces; bulk actions; queues—density never excuses missing labels, focus, or keyboard paths.

---

## 16. Error Accessibility

Clear explanation; associated fields when validation; understandable next action; no sensitive internals.

---

## 17. Responsive Accessibility

Touch targets; reflow; no inaccessible hover-only critical actions; assessment usable on mobile.

---

## 18. Localization Accessibility

Bangla; English; mixed content; text expansion; medical terminology—names and errors remain understandable when strings grow.

---

## 19. Reduced Motion

Motion is purposeful; reduced-motion preference removes or minimizes non-essential motion without removing information.

---

## 20. Color and Contrast

Follow semantic contrast intent from [`12`](12-design-system.md). No new exact numeric values unless already mandated by locked docs. Status never color-only.

---

## 21. Touch and Pointer Accessibility

Adequate targets; avoid precision-only critical controls; pointer cancellation considerations conceptually.

---

## 22. Zoom and Text Resizing

Layouts tolerate zoom/text resizing without trapping or clipping critical controls/content.

---

## 23. Loading / Async Accessibility

Loading is perceivable; completion/errors announced appropriately; avoid indefinite silent waits.

---

## 24. HTMX Accessibility Boundary

Partial updates must preserve focus strategy, names, and announcements. HTMX must not become an accessibility bypass or authorization boundary.

---

## 25. Alpine Accessibility Boundary

Local UI (dropdowns, disclosures, modals) must remain keyboard and screen-reader operable. Alpine must not own access control.

---

## 26. Accessibility Testing Strategy

Conceptual: keyboard; screen reader; focus; responsive; localization; forms; assessment; regression.

Complements component/page/interaction tests; does not replace security/domain tests.

---

## 27. Accessibility Governance

Ownership; review gates; regression prevention; breaking changes; exceptions require justification.

---

## 28. Future-only Extensions

**Future-only:** advanced assistive personalization; Offline Mode a11y variants; Flutter a11y bridge specifics; AI Tutor a11y surfaces.

Must not silently become V1 requirements.

---

## 29. Cross References

| Document | Use |
| --- | --- |
| [`11`](11-ui-ux-specification.md)–[`18`](18-frontend-interaction-architecture.md) | Prior a11y expectations |
| [`19`](19-frontend-form-validation-architecture.md) | Form accessibility alignment (draft) |
| [`07`](07-security-and-session-management.md) | Security-safe messaging |

**This document does not modify any approved document.**

---

## 30. Acceptance Criteria

Accept when: principles, ownership, semantic structure, naming, keyboard, focus, screen reader, forms/nav/modal/assessment/learning/library/staff/error/responsive/localization contracts, reduced motion, color/contrast, touch, zoom, loading, HTMX/Alpine boundaries, testing, governance, and Future-only extensions are defined; **no** implementation source generated; docs `00`–`19` not substantively modified by this document.

---

## 31. Document Lock

**Status:** `docs/20-frontend-accessibility-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend accessibility architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`19` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*

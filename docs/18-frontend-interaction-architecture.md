# Nursilo — Frontend Interaction Architecture

| Field | Value |
| --- | --- |
| Document | `18-frontend-interaction-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`17`](17-frontend-styling-architecture.md) (all Approved v1.0.0 — LOCKED; **unchanged** by this document) |
| Purpose | Authoritative conceptual frontend interaction architecture for Nursilo V1 |
| Out of scope | HTML; CSS; Tailwind classes; JavaScript source; Alpine source; HTMX attributes; Django templates; Python; APIs; database implementation; configuration files; Figma; implementation artifacts |
| Nature | **Additive only** — does not modify locked docs `00`–`17` |

---

## 1. Purpose

Nursilo needs an **interaction architecture** so learner, staff, and admin surfaces behave predictably: same feedback language, clear server/client ownership, progressive enhancement, accessible controls, and graceful failure—without inventing business truth in the browser.

| Layer | Authority |
| --- | --- |
| [`12`](12-design-system.md) | Visual design |
| [`13`](13-frontend-architecture.md) | Frontend technology & boundaries |
| [`14`](14-frontend-component-architecture.md) | Component structure |
| [`15`](15-frontend-page-architecture.md) | Page composition |
| [`16`](16-frontend-template-architecture.md) | Template structure |
| [`17`](17-frontend-styling-architecture.md) | Styling |
| **This document** | Interaction behavior |
| Future implementation | Actual HTMX / Alpine / form wiring |

```text
12 Design System
    ↓
13 Frontend Architecture
    ↓
14 Component Architecture
    ↓
15 Page Architecture
    ↓
16 Template Architecture
    ↓
17 Styling Architecture
    ↓
18 Interaction Architecture
    ↓
Future implementation
```

Goals: predictable behavior; consistent feedback; server/client responsibility; progressive enhancement; accessible and responsive interactions; graceful failure; shared patterns across surfaces.

---

## 2. Interaction Architecture Principles

| Principle | Meaning |
| --- | --- |
| Server truth | Confirmed outcomes come from the server |
| Progressive enhancement | Core flows work without heavy client logic |
| Minimal client behavior | Browser enhances; does not decide business outcomes |
| Explicit state transitions | Idle → loading → success/error is visible and named |
| Immediate understandable feedback | Users know what happened next |
| Accessibility by default | Keyboard, focus, announcements |
| Keyboard-first compatibility | All critical actions reachable without pointer |
| Mobile-first interaction | Touch-friendly learner flows |
| Localization-safe interaction | Bangla/English expansion |
| Reuse before duplication | Shared interaction vocabulary |
| No duplicated business rules | Rules stay in domain/services ([`09`](09-business-rules.md)) |
| No client authorization / entitlement / scoring / payment authority | Server decides |
| Graceful degradation | Partial enhancement fails safely |
| Recoverability | Clear next action after failure |
| Predictability & consistency | Same pattern for same intent |
| Performance without premature complexity | Correctness and security first |

---

## 3. Interaction Layer Model

```text
User
 ↓
Page
 ↓
Component
 ↓
Interaction
 ↓
Presentation boundary
 ↓
Application / domain service
 ↓
Server truth
```

| Mode | Ownership |
| --- | --- |
| **Local UI interaction** | Temporary browser presentation only |
| **Server-enhanced interaction** | Request → server result → UI update |
| **Full navigation** | Clean IA / security / assessment transitions |
| **Progressive enhancement** | Base HTML forms/links work; HTMX/Alpine optional |

No interaction layer may authorize, entitle, score, or confirm payment.

---

## 4. Interaction Types

| Type | Purpose | Typical trigger | Expected response | State ownership | A11y | Enhancement |
| --- | --- | --- | --- | --- | --- | --- |
| **A. Navigation** | Change place/context | Link / menu | New page or major view | Server route/session | Focus to main content | Full nav preferred for major IA |
| **B. Form** | Submit structured input | Submit | Validate / persist / error | Server | Field-associated errors | Full post or enhanced submit |
| **C. Selection** | Choose option/item | Click/keyboard | Selected presentation | Local until saved; server after save | Focus & selected state | Local or partial |
| **D. Toggle** | Binary preference/UI | Switch | On/off presentation | Local or server per field | Role/state announced | Alpine or server |
| **E. Disclosure** | Show/hide detail | Expand | Expanded/collapsed | Local UI | Expandable semantics | Alpine |
| **F. Search** | Find content | Input/submit | Result set | Server results | Announce result count where useful | HTMX partial |
| **G. Filter** | Narrow set | Control change | Filtered set | Server | Preserve context | HTMX partial |
| **H. Pagination** | Move through sets | Page control | Next page set | Server | Focus management | HTMX partial |
| **I. Modal/dialog** | Focused task | Open action | Dialog content | Content from server when loaded | Focus trap/restore | Alpine + optional HTMX load |
| **J. Notification** | Inform / mark read | Open / mark | Read state update | Server | Status announcements | HTMX partial |
| **K. Bookmark** | Save/unsave item | Toggle | Bookmark state | Server | State announced | HTMX partial |
| **L. Assessment** | Answer / navigate / submit | Option / nav / submit | Attempt state update | Server attempt | Timer & focus careful | Mixed; server authoritative |
| **M. Learning** | Navigate / complete | Open lesson | Progress presentation | Server progress | Clear hierarchy | Full or partial |
| **N. Reader** | Read / bookmark | Page turn / bookmark | Reading/access state | Server for access & bookmarks | Readable controls | Local chrome + server actions |
| **O. Subscription/payment** | Upgrade / pay | CTA / checkout | Pending/success/fail | Server payment truth | Clear status | Full nav for confirmation |
| **P. Staff/admin ops** | Review / publish / manage | Table / action | Workflow result | Server + RBAC | Dense but keyboardable | Partial + confirmations |
| **Q. Auth/security** | Identity / session | Login / re-auth | Authenticated state | Server session | Clear errors, no leakage | Full nav often |
| **R. Error/recovery** | Restore flow | Retry / go home | Recovered or safe exit | Server | Clear next action | Full or partial |

---

## 5. Interaction State Model

Conceptual lifecycle:

```text
Idle
→ Triggered
→ Loading
→ Server response
→ Success / Error / Conflict
→ Stable state
```

Additional states: disabled; unavailable; permission denied; entitlement denied; session expired; cancelled; retryable; non-retryable.

**Rule:** State must never imply a result the server has not confirmed.

---

## 6. Full Navigation Interactions

Prefer full page navigation when:

- Major IA changes occur  
- Authentication transitions occur  
- Entering or leaving assessment sessions  
- Entering reader mode (clean focus shell)  
- Completing major workflows  
- Security-sensitive transitions  
- Payment completion needs a clean, server-confirmed state  

Full navigation remains important despite HTMX: it resets context cleanly, clarifies focus layouts, and reduces stale partial-page risk for high-stakes flows.

---

## 7. Partial Update Interactions

Appropriate for: search; filtering; pagination; notification read state; bookmarks; inline form updates; staff queue updates; dashboard refresh; modal content; non-critical content refresh.

Conceptual cycle:

```text
Request → Loading state → Server response → Replacement/update → Final state
```

Server response remains authoritative.

---

## 8. Local UI Interactions

Appropriate for local browser state: dropdown; tab selection; disclosure; modal visibility; password visibility; temporary selection; temporary UI preference; visual countdown display.

Local UI state **cannot** become business truth (auth, entitlement, score, payment, session validity, workflow).

---

## 9. Form Interaction Architecture

States: initial; editing; validation; submission; success; failure; retry.

| Rule |
| --- |
| Server validation is authoritative |
| Client hints are optional |
| Validation errors are localized and field-associated |
| Form summaries where appropriate |
| Sensitive forms follow [`07`](07-security-and-session-management.md) |
| Duplicate submission handled safely |
| Destructive actions require appropriate confirmation |

---

## 10. Button / Action Interaction Architecture

Action kinds: primary; secondary; tertiary; destructive; icon; grouped; asynchronous.

States: idle; hover; focus; disabled; loading; success; failure.

Prevent accidental repeated submission where relevant (especially payments, exam submit, destructive bulk actions).

---

## 11. Loading Architecture

Scopes: page; section; component; action; search; pagination; assessment.

| Rule |
| --- |
| Loading must be understandable |
| Avoid misleading progress |
| Preserve layout stability where practical |
| Do not hide errors behind indefinite loading |
| Avoid unnecessary spinners |
| Use skeleton/placeholder patterns where appropriate |

---

## 12. Feedback Architecture

Kinds: success; error; warning; information; validation; security; entitlement; payment; assessment.

| Placement | When |
| --- | --- |
| Inline / near action | Field errors; small toggles |
| Page-level | Workflow outcomes; auth; payment |
| Temporary | Non-critical success toasts/alerts |
| Persistent | Blocking errors; security notices; payment pending |

Never expose sensitive information.

---

## 13. Search / Filter / Pagination Interactions

| Flow | Cycle |
| --- | --- |
| Search | Input → loading → results → empty/error |
| Filtering | Selection → update → result state |
| Pagination | Page selection → loading → updated results |

Rules: preserve context; maintain accessible focus; keyboard and mobile support; avoid unnecessary full navigation when partial update fits; server determines results.

---

## 14. Modal / Drawer / Popover Interactions

Lifecycle: opening; closing; confirmation; cancellation; loading content; error; focus entry; focus restoration.

| Rule |
| --- |
| Focused task only |
| Keyboard accessible |
| Escape where appropriate |
| No unnecessary modal stacking |
| Critical content cannot exist only inside tooltips/popovers |

---

## 15. Notification Interactions

Behaviors: open notification center; mark read; unread indicator; announcement opening; security notification handling; priority behavior.

| Rule |
| --- |
| Server owns read/unread state |
| No fake notification state |
| No secret information |
| Accessible status communication |

---

## 16. Authentication / Security Interactions

Flows: login; logout; session expiration; email verification; password reset; password change; re-authentication; device management; logout all sessions; security notification.

| Rule |
| --- |
| Server owns authentication state |
| Browser state is not proof |
| Expired sessions require re-authentication |
| Sensitive actions need confirmation / re-auth as per docs/07 |
| Avoid user enumeration leakage |
| Never expose secrets |

---

## 17. Entitlement / Premium Interactions

States: Free content; Premium content; Locked content; Upgrade; Pending entitlement; Expired entitlement; Failed payment.

| Rule |
| --- |
| Server owns entitlement |
| UI only presents state |
| No optimistic premium access |
| No fake urgency or manipulative patterns |
| Preserve Free user value |

---

## 18. Assessment Interaction Architecture

Flows: practice/exam setup; question selection; answer selection; question navigation; flagging; review navigation; timer display; submit; auto-submit; submission confirmation; result viewing; review.

| Server authority (mandatory) |
| --- |
| Attempt; timer; question version; answer persistence; submission; scoring; completion |

Client interaction only presents and requests state transitions.

---

## 19. Assessment Failure / Recovery

Conceptual handling for: network interruption; submission failure; session expiry; server conflict; stale attempt; unavailable question; timer synchronization issue; duplicate submission; browser refresh; accidental navigation.

Do not invent business rules. Follow [`07`](07-security-and-session-management.md) and [`09`](09-business-rules.md). UI communicates server outcomes and safe next actions only.

---

## 20. Learning Interaction Architecture

Flows: course navigation; subject/unit/chapter/topic navigation; lesson opening; material interaction; completion; progress update; continue learning; weak/strong topic navigation; study goal interaction.

Progress mutations remain server authoritative.

---

## 21. Library / Reader Interaction Architecture

Flows: catalog search; filtering; book opening; reader navigation; bookmark; download request; premium access; access denial; reader controls.

Storage URLs/keys are never treated as authorization.

---

## 22. Subscription / Payment Interactions

Flows: plan selection; upgrade; checkout transition; payment pending; payment success; payment failure; billing status; retry/recovery.

**Critical rule:** Payment success must come from server-confirmed state. Never display payment success based solely on client-side events.

---

## 23. Staff / Admin Interactions

Flows: search; filter; table selection; bulk actions; approval; rejection; publishing; queue refresh; content editing; review workflow; audit viewing; report interaction.

| Rule |
| --- |
| Server controls authorization |
| Destructive actions require appropriate confirmation |
| Workflow transitions come from approved business rules ([`09`](09-business-rules.md)) |
| Components/pages do not invent workflow states |

---

## 24. HTMX Interaction Boundary

| May enhance | Must never own |
| --- | --- |
| Search; filters; pagination | Authorization / RBAC |
| Inline updates; notification read; bookmark | Entitlement |
| Modal content; staff queue refresh | Scoring |
| Dashboard partial refresh | Payment truth; session truth; business-rule authority |

Do not generate HTMX attributes in this document.

---

## 25. Alpine Interaction Boundary

| Appropriate | Must never own |
| --- | --- |
| Dropdowns; tabs; disclosure | Authorization; entitlement |
| Modal visibility; password visibility | Scoring; payment truth |
| Temporary UI state; visual countdown display | Session truth; persistence; workflow authority |

Do not generate Alpine source in this document.

---

## 26. Event / Action Flow

```text
User intent
→ Interaction trigger
→ Presentation request
→ Server / service operation
→ Server result
→ UI state update
→ Feedback
```

The browser requests actions but does not authorize or finalize business outcomes.

---

## 27. Navigation / Transition Architecture

| Category | Use |
| --- | --- |
| Full page transition | Major IA; auth; exam enter/exit; payment confirmation |
| Partial update | Search/filter/pagination; small state toggles |
| Modal transition | Focused secondary tasks / confirmations |
| Inline transition | Local disclosure / temporary UI |
| Redirect after success | Post-auth; completed workflows |
| Redirect after authentication | Resume intended destination when safe |
| Recovery transition | Session expired; permission denied; errors |

Map to page families in [`15`](15-frontend-page-architecture.md).

---

## 28. Accessibility Interaction Contract

Every interaction must consider: keyboard access; focus entry/retention/restoration; accessible names; state announcements; loading/error announcements; confirmation communication; reduced motion; touch interaction; zoom/text resizing.

Do not rely on color alone.

---

## 29. Localization Interaction Contract

Interactions must tolerate: Bangla; English; mixed-language content; longer labels; localized errors and confirmations; localized dates/numbers/currency; medical terminology.

Do not assume English string lengths.

---

## 30. Responsive Interaction Architecture

| Viewport | Behavior |
| --- | --- |
| Mobile | Touch-first; clear actions; compact navigation; accessible forms; assessment usable |
| Tablet | Adaptive layouts; comfortable spacing |
| Desktop | Keyboard efficiency; staff/admin productivity; wider content where appropriate |
| Large desktop | Extra space without excessive interaction distance |

---

## 31. Performance / Interaction Efficiency

Avoid unnecessary requests; avoid excessive client JavaScript; prefer partial updates where appropriate; avoid excessive DOM mutation; conceptual debounce for search where justified; keep assessment interaction lightweight; preserve responsive feedback; avoid blocking UI unnecessarily.

Correctness and security outrank micro-optimization.

---

## 32. Error / Recovery Architecture

Recover for: validation failure; network failure; server error; permission denial; entitlement denial; session expiration; business conflict; maintenance; unavailable content.

Every recoverable failure should provide an understandable next action.

---

## 33. Offline / Best-Effort Interaction

Conceptual behavior only. Do **not** introduce Offline Mode as a V1 business requirement.

Where offline/best-effort states exist: clearly communicate uncertainty; never falsely confirm persistence, payment, or assessment submission; never imply server state without server confirmation.

---

## 34. Interaction Data Contract

Conceptual data: labels; actions/URLs; current state; loading state; success/error state; accessibility metadata; server-provided status; permission-aware presentation; entitlement-aware presentation; localized messages.

Interactions must not query repositories.

---

## 35. Security-Aware Interactions

Never expose: passwords; tokens; session identifiers; secrets; private payment information; internal filesystem paths; protected content.

Interactions must **not** create a false security boundary through: disabled buttons alone; hidden controls alone; client-only validation; client-only role checks; client-only entitlement checks.

---

## 36. Interaction Composition Rules

| Rule |
| --- |
| Interactions should be reusable |
| Page interactions compose component interactions |
| Components should not own unrelated page workflows |
| Avoid unnecessarily deep interaction chains |
| Avoid hidden side effects |
| Action names should be predictable |
| Feedback belongs to the action/context that caused it |

Preferred:

```text
Page → Section → Pattern → Component → Interaction → Server action
```

---

## 37. Interaction Naming Conventions

Names describe user intent, domain, action, and state where needed.

| Good | Avoid |
| --- | --- |
| SearchCourses, SubmitAnswer, MarkNotificationRead, BookmarkBook, StartPractice, SubmitExam, UpgradeSubscription, ChangePassword, ApproveContent | DoThing, MagicAction, HandleStuff, ClickHandler1, ProcessFinal |

---

## 38. Interaction Reuse Rules

Before creating a new interaction:

1. Search existing interaction vocabulary.  
2. Determine whether an existing pattern applies.  
3. Reuse when semantics are the same.  
4. Extend only when behavior remains coherent.  
5. Create a new interaction only when reuse harms clarity.  
6. Document meaningful new interaction patterns.  

---

## 39. Interaction Testing Strategy

Conceptual tests: trigger; loading; success; failure; retry; keyboard; focus; screen reader; responsive; localization; HTMX enhancement; Alpine enhancement; authentication; entitlement; assessment; payment state; regression.

Interaction tests do **not** replace service/domain/business-rule tests.

---

## 40. Interaction Documentation

Future significant interactions should document: purpose; trigger; expected states; server authority; client behavior; accessibility; localization; responsive behavior; HTMX/Alpine behavior if applicable; error/recovery; security considerations.

Do not create implementation documentation now.

---

## 41. Interaction Governance

Ownership; UX review; accessibility review; security review; frontend architecture review; duplication prevention; breaking changes; deprecation; technical debt; interaction consistency.

New interaction patterns require justification.

---

## 42. Future Interaction Extensions

**Future-only:** Offline Mode; AI Tutor interactions; Adaptive Learning interactions; Institution Portal interactions; Flutter-specific patterns; advanced real-time collaboration; advanced visualization interactions; dark-mode-specific interaction behavior.

Must not silently become V1 requirements.

---

## 43. Cross References

| Document | Use |
| --- | --- |
| [`03`](03-user-roles.md) | Role-aware presentation |
| [`04`](04-system-architecture.md) | Presentation → services |
| [`05`](05-domain-model.md) | Domain hierarchy |
| [`07`](07-security-and-session-management.md) | Auth/session interactions |
| [`08`](08-api-design.md) | Future clients |
| [`09`](09-business-rules.md) | Workflow & assessment/payment truth |
| [`10`](10-development-roadmap.md) | Delivery scope |
| [`11`](11-ui-ux-specification.md) | Experience expectations |
| [`12`](12-design-system.md) | Visual feedback language |
| [`13`](13-frontend-architecture.md) | HTMX/Alpine tech boundaries |
| [`14`](14-frontend-component-architecture.md) | Component interaction hosts |
| [`15`](15-frontend-page-architecture.md) | Page transitions |
| [`16`](16-frontend-template-architecture.md) | Fragment boundaries |
| [`17`](17-frontend-styling-architecture.md) | Loading/feedback presentation |

**This document does not modify any approved document.**

---

## 44. Acceptance Criteria

This document is acceptable when:

1. Purpose, principles, layer model, interaction types, and state lifecycle are defined  
2. Full navigation, partial update, and local UI interactions are defined  
3. Form, button/action, loading, and feedback architectures are defined  
4. Search/filter/pagination and modal/drawer/popover interactions are defined  
5. Notification, authentication/security, and entitlement/premium interactions are defined  
6. Assessment interactions and failure/recovery are defined  
7. Learning, library/reader, subscription/payment, and staff/admin interactions are defined  
8. HTMX and Alpine boundaries are defined  
9. Event/action flow and navigation/transition architecture are defined  
10. Accessibility, localization, and responsive interaction contracts are defined  
11. Performance, error/recovery, and offline/best-effort boundaries are defined  
12. Data contract, security-aware rules, composition, naming, and reuse rules are defined  
13. Testing, documentation expectations, governance, and Future-only extensions are defined  
14. **No** implementation source code is generated  
15. **No** API/database implementation is generated  
16. Docs `00`–`17` remain unchanged  

---

## 45. Document Lock

**Status:** `docs/18-frontend-interaction-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual frontend interaction architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`17` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*
